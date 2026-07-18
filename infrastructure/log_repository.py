import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime

from starlette.concurrency import run_in_threadpool


class LogRepository(ABC):
    @abstractmethod
    async def guardar(self, user_id: int, consulta: str, respuesta: str | None, resuelta: bool) -> None:
        pass


class SQLiteLogRepository(LogRepository):
    def __init__(self, path: str):
        self._path = path
        self._crear_tabla()

    def _crear_tabla(self) -> None:
        with sqlite3.connect(self._path) as conn:
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
