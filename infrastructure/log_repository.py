import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime

from starlette.concurrency import run_in_threadpool


class LogRepository(ABC):
    @abstractmethod
    async def guardar(self, user_id: int, consulta: str, respuesta: str | None, resuelta: bool) -> None:
        pass

    @abstractmethod
    async def obtener_metricas(self) -> dict:
        pass

    @abstractmethod
    async def obtener_logs_recientes(self, limite: int = 20) -> list[dict]:
        pass

    @abstractmethod
    async def obtener_topicos_mas_consultados(self) -> list[dict]:
        pass


class SQLiteLogRepository(LogRepository):
    def __init__(self, path: str):
        self._path = path
        self._crear_tabla()

    def _crear_tabla(self) -> None:
        with sqlite3.connect(self._path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id   INTEGER NOT NULL,
                    consulta  TEXT    NOT NULL,
                    respuesta TEXT,
                    resuelta  INTEGER NOT NULL,
                    fecha     TEXT    NOT NULL
                )
            """)

    def _guardar_sync(self, user_id: int, consulta: str, respuesta: str | None, resuelta: bool) -> None:
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                "INSERT INTO logs (user_id, consulta, respuesta, resuelta, fecha) VALUES (?, ?, ?, ?, ?)",
                (user_id, consulta, respuesta, int(resuelta), datetime.now().isoformat()),
            )

    async def guardar(self, user_id: int, consulta: str, respuesta: str | None, resuelta: bool) -> None:
        await run_in_threadpool(self._guardar_sync, user_id, consulta, respuesta, resuelta)

    def _obtener_metricas_sync(self) -> dict:
        with sqlite3.connect(self._path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as total, SUM(resuelta) as resueltas FROM logs")
            row = cursor.fetchone()
            total = row["total"] or 0
            resueltas = row["resueltas"] or 0
            tasa_exito = (resueltas / total * 100) if total > 0 else 100.0
            
            cursor.execute("SELECT COUNT(DISTINCT user_id) as sesiones FROM logs")
            row_sesiones = cursor.fetchone()
            sesiones = row_sesiones["sesiones"] or 0
            
            import os
            archivos = 0
            if os.path.exists("static/uploads"):
                archivos = len([f for f in os.listdir("static/uploads") if os.path.isfile(os.path.join("static/uploads", f))])
            
            return {
                "total_consultas": total,
                "tasa_exito": round(tasa_exito, 2),
                "sesiones_activas": sesiones,
                "total_archivos": archivos
            }

    async def obtener_metricas(self) -> dict:
        return await run_in_threadpool(self._obtener_metricas_sync)

    def _obtener_logs_recientes_sync(self, limite: int) -> list[dict]:
        with sqlite3.connect(self._path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, user_id, consulta, respuesta, resuelta, fecha FROM logs ORDER BY id DESC LIMIT ?",
                (limite,)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    async def obtener_logs_recientes(self, limite: int = 20) -> list[dict]:
        return await run_in_threadpool(self._obtener_logs_recientes_sync, limite)

    def _obtener_topicos_mas_consultados_sync(self) -> list[dict]:
        with sqlite3.connect(self._path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT consulta FROM logs")
            rows = cursor.fetchall()
            
            from services.ade_taxonomy import ADE_CATEGORIES
            counts = {cat: 0 for cat in ADE_CATEGORIES.keys()}
            counts["otros"] = 0
            
            for row in rows:
                consulta = (row["consulta"] or "").lower()
                matched = False
                for cat, terms in ADE_CATEGORIES.items():
                    if any(term in consulta for term in terms):
                        counts[cat] += 1
                        matched = True
                if not matched:
                    counts["otros"] += 1
            
            res = [{"topic": k, "count": v} for k, v in counts.items() if v > 0 or k != "otros"]
            res.sort(key=lambda x: x["count"], reverse=True)
            return res

    async def obtener_topicos_mas_consultados(self) -> list[dict]:
        return await run_in_threadpool(self._obtener_topicos_mas_consultados_sync)
