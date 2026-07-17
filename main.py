import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ingesta.document_loader import cargar_documento_desde_bytes
from infrastructure.llm_client import GeminiLLMClient, GroqLLMClient
from infrastructure.log_repository import SQLiteLogRepository
from infrastructure.vector_store import ChromaVectorStore
from services.chat_service import ChatService
from services.session_store import SessionDocumentStore

load_dotenv()

Path(os.getenv("SQLITE_PATH", "./db/logs.db")).parent.mkdir(parents=True, exist_ok=True)

ALLOWED_FILE_EXTENSIONS = {".pdf", ".txt", ".docx", ".png", ".jpg", ".jpeg", ".glb", ".gltf", ".obj"}

_chat_service: ChatService | None = None
_session_store: SessionDocumentStore | None = None


class MensajeRequest(BaseModel):
    mensaje: str
    session_id: str = "anonimo"


def _crear_llm_client() -> GeminiLLMClient | GroqLLMClient:
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        return GroqLLMClient(
            api_key=groq_key,
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        )
    return GeminiLLMClient(
        api_key=os.getenv("GEMINI_API_KEY"),
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _chat_service, _session_store
    _session_store = SessionDocumentStore()
    _chat_service = ChatService(
        vector_store=ChromaVectorStore(
            path=os.getenv("CHROMA_PATH", "./db/chroma"),
            api_key=os.getenv("GEMINI_API_KEY", ""),
        ),
        llm_client=_crear_llm_client(),
        log_repository=SQLiteLogRepository(
            path=os.getenv("SQLITE_PATH", "./db/logs.db"),
        ),
        top_k=int(os.getenv("TOP_K", 4)),
        similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", 0.60)),
    )
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/api/chat")
async def chat(request: MensajeRequest):
    documentos_sesion = await _session_store.list(request.session_id)
    contexto_extra = ""
    if documentos_sesion:
        partes = [
            f"[{doc.filename}]\n" + "\n".join(doc.chunks)
            for doc in documentos_sesion
        ]
        contexto_extra = "\n\n---\n\n".join(partes)

    user_id = abs(hash(request.session_id)) % (2 ** 31)
    respuesta = await _chat_service.procesar_consulta(
        texto=request.mensaje,
        user_id=user_id,
        contexto_extra=contexto_extra,
    )
    return {"respuesta": respuesta}


@app.get("/api/fuentes")
async def fuentes(session_id: str = "anonimo"):
    documentos = await _session_store.list(session_id)
    return {"archivos": [doc.filename for doc in documentos]}


@app.post("/api/upload")
async def upload(archivo: UploadFile = File(...), session_id: str = Form("anonimo")):
    extension = Path(archivo.filename).suffix.lower()
    if extension not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Formato no soportado. Solo se aceptan PDF, TXT, DOCX, PNG, JPG, JPEG, GLB, GLTF y OBJ.",
        )

    contenido = await archivo.read()
    try:
        documentos = cargar_documento_desde_bytes(archivo.filename, contenido)
    except Exception:
        documentos = []

    if not documentos:
        return JSONResponse({"error": "No se pudo extraer texto del archivo."}, status_code=422)

    chunks = [doc.page_content for doc in documentos]
    await _session_store.add(session_id, archivo.filename, chunks, "pdf", {})
    return {"archivo": archivo.filename, "paginas": len(chunks)}


@app.delete("/api/upload")
async def delete_upload(session_id: str, filename: str):
    await _session_store.remove(session_id, filename)
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
