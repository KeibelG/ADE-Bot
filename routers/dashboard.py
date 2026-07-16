from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/metrics")
async def get_metrics(request: Request):
    chat_service = getattr(request.app.state, "chat_service", None)
    if not chat_service:
        raise HTTPException(status_code=500, detail="Servicio de chat no inicializado en app.state")
    return await chat_service._logs.obtener_metricas()


@router.get("/logs/recent")
async def get_recent_logs(request: Request, limit: int = 20):
    chat_service = getattr(request.app.state, "chat_service", None)
    if not chat_service:
        raise HTTPException(status_code=500, detail="Servicio de chat no inicializado en app.state")
    return await chat_service._logs.obtener_logs_recientes(limit)


@router.get("/topics")
async def get_topics(request: Request):
    chat_service = getattr(request.app.state, "chat_service", None)
    if not chat_service:
        raise HTTPException(status_code=500, detail="Servicio de chat no inicializado en app.state")
    return await chat_service._logs.obtener_topicos_mas_consultados()
