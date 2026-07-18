import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma

from ingesta.document_loader import cargar_documento
from infrastructure.google_embeddings import GoogleGenAIEmbeddings

load_dotenv()

_ETIQUETAS = {
    "pensum": "Pensum y Materias",
    "licitacion": "Licitaciones y Contratos",
    "proceso": "Trámites Administrativos",
    "plano": "Normas de Diseño",
    "financiero": "Presupuesto y Finanzas",
    "seguridad": "Seguridad en Obras",
}


def _detectar_etiqueta(nombre: str) -> str:
    nombre_lower = nombre.lower()
    for clave, etiqueta in _ETIQUETAS.items():
        if clave in nombre_lower:
            return etiqueta
    return "General"


def ejecutar(docs_path: str | None = None) -> None:
    datos_path = Path(docs_path) if docs_path else Path("datos")
    extensiones_aceptadas = {".pdf", ".txt", ".docx", ".png", ".jpg", ".jpeg", ".glb", ".gltf", ".obj"}
    archivos = [
        archivo
        for archivo in datos_path.iterdir()
        if archivo.is_file() and archivo.suffix.lower() in extensiones_aceptadas
    ]

    if not archivos:
        print(f"No se encontraron archivos válidos en {datos_path}/")
        return

    api_key = (
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("CHROMA_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )
    if not api_key:
        raise RuntimeError(
            "Debe configurar GOOGLE_API_KEY, CHROMA_API_KEY o GEMINI_API_KEY para generar embeddings."
        )

    chunk_size = os.getenv("INGEST_CHUNK_SIZE", "2000")
    chunk_overlap = os.getenv("INGEST_CHUNK_OVERLAP", "250")
    embedding_model = os.getenv("GOOGLE_GENAI_EMBEDDING_MODEL", "gemini-embedding-001")
    print(f"Usando modelo de embedding: {embedding_model}")
    print(f"Usando chunk size: {chunk_size}, overlap: {chunk_overlap}")

    embeddings = GoogleGenAIEmbeddings(
        api_key=api_key,
        model=embedding_model,
    )
    fragmentos_totales = []

    for archivo in archivos:
        print(f"Procesando: {archivo.name}")
        documentos = cargar_documento(archivo)
        if not documentos:
            print(f"  Saltando {archivo.name}: no se generó contenido." )
            continue

        etiqueta = _detectar_etiqueta(archivo.stem)
        for documento in documentos:
            documento.metadata["tema"] = etiqueta
            documento.metadata["fuente"] = archivo.name

        fragmentos_totales.extend(documentos)
        print(f"  {len(documentos)} fragmentos generados [{etiqueta}]")

    chroma_path = os.getenv("CHROMA_PATH") or "./db/chroma"
    if Path(chroma_path).exists():
        shutil.rmtree(chroma_path)

    Chroma.from_documents(
        documents=fragmentos_totales,
        embedding=embeddings,
        persist_directory=chroma_path,
    )

    print(f"\nIngesta completada. {len(fragmentos_totales)} fragmentos indexados.")


if __name__ == "__main__":
    ejecutar()
