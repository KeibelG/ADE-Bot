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
from routers.dashboard import router as dashboard_router

load_dotenv()

Path(os.getenv("SQLITE_PATH", "./db/logs.db")).parent.mkdir(parents=True, exist_ok=True)

ALLOWED_FILE_EXTENSIONS = {".pdf", ".txt", ".docx", ".png", ".jpg", ".jpeg", ".glb", ".gltf", ".obj"}

_chat_service: ChatService | None = None
_session_store: SessionDocumentStore | None = None


class MediaItem(BaseModel):
    mime_type: str
    data: str  # Base64 data string
    filename: str | None = None


class MensajeRequest(BaseModel):
    mensaje: str
    session_id: str = "anonimo"
    media: list[MediaItem] | None = None


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
    
    llm_default = _crear_llm_client()
    multimodal_llm = None
    if isinstance(llm_default, GroqLLMClient):
        multimodal_llm = GeminiLLMClient(
            api_key=os.getenv("GEMINI_API_KEY"),
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
        )
    
    _chat_service = ChatService(
        vector_store=ChromaVectorStore(
            path=os.getenv("CHROMA_PATH", "./db/chroma"),
            api_key=os.getenv("GEMINI_API_KEY", ""),
        ),
        llm_client=llm_default,
        log_repository=SQLiteLogRepository(
            path=os.getenv("SQLITE_PATH", "./db/logs.db"),
        ),
        top_k=int(os.getenv("TOP_K", 4)),
        similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", 0.60)),
        multimodal_llm_client=multimodal_llm,
    )
    app.state.chat_service = _chat_service
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(dashboard_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/api/chat")
async def chat(request: MensajeRequest):
    import base64
    documentos_sesion = await _session_store.list(request.session_id)
    media_files: list[dict[str, str]] = []

    if request.media:
        for m in request.media:
            media_files.append({
                "mime_type": m.mime_type,
                "data": m.data
            })

    partes = []
    for doc in documentos_sesion:
        if doc.chunks:
            partes.append(f"[{doc.filename}]\n" + "\n".join(doc.chunks))

        ext = Path(doc.filename).suffix.lower()
        filepath = Path("static/uploads") / doc.filename
        if filepath.exists():
            mime_type = None
            if ext in {".png", ".jpg", ".jpeg"}:
                mime_type = f"image/{ext[1:]}"
                if ext == ".jpg":
                    mime_type = "image/jpeg"
            elif ext == ".pdf":
                mime_type = "application/pdf"

            if mime_type:
                try:
                    data_bytes = filepath.read_bytes()
                    data_b64 = base64.b64encode(data_bytes).decode("utf-8")
                    if not any(item["data"] == data_b64 for item in media_files):
                        media_files.append({
                            "mime_type": mime_type,
                            "data": data_b64
                        })
                except Exception:
                    pass

    contexto_extra = "\n\n---\n\n".join(partes)

    user_id = abs(hash(request.session_id)) % (2 ** 31)
    respuesta = await _chat_service.procesar_consulta(
        texto=request.mensaje,
        user_id=user_id,
        contexto_extra=contexto_extra,
        media_files=media_files or None
    )

    urls_recursos = []
    for doc in documentos_sesion:
        ext = Path(doc.filename).suffix.lower()
        if ext in {".glb", ".gltf", ".obj", ".png", ".jpg", ".jpeg"}:
            urls_recursos.append({
                "filename": doc.filename,
                "url": f"/static/uploads/{doc.filename}",
                "tipo": "3d" if ext in {".glb", ".gltf", ".obj"} else "render"
            })

    return {
        "respuesta": respuesta,
        "recursos": urls_recursos
    }


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
    
    upload_dir = Path("static/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    filepath = upload_dir / archivo.filename
    filepath.write_bytes(contenido)

    try:
        documentos = cargar_documento_desde_bytes(archivo.filename, contenido)
    except Exception:
        documentos = []

    chunks = [doc.page_content for doc in documentos] if documentos else [f"Archivo de diseño/modelo: {archivo.filename}"]
    await _session_store.add(session_id, archivo.filename, chunks, "pdf", {})
    
    public_url = f"/static/uploads/{archivo.filename}"
    return {
        "archivo": archivo.filename,
        "paginas": len(chunks),
        "url": public_url
    }


@app.delete("/api/upload")
async def delete_upload(session_id: str, filename: str):
    await _session_store.remove(session_id, filename)
    
    # También intentar borrar físicamente de static/uploads
    filepath = Path("static/uploads") / filename
    if filepath.exists():
        try:
            filepath.unlink()
        except Exception:
            pass
            
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
