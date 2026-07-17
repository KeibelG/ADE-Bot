import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SESSION_STORE_PATH = Path(os.getenv("SESSION_STORE_PATH", "./db/sessions"))


@dataclass
class SessionDocument:
    filename: str
    chunks: list[str]
    resource_type: str
    metadata: dict[str, Any]

    @property
    def page_content(self) -> str:
        return "\n".join(self.chunks)


class SessionDocumentStore:
    def __init__(self) -> None:
        self._storage_dir = SESSION_STORE_PATH
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _session_file(self, session_id: str) -> Path:
        safe_id = session_id.replace("/", "_").replace("\\", "_")
        return self._storage_dir / f"{safe_id}.json"

    async def _read_session(self, session_id: str) -> list[dict[str, Any]]:
        path = self._session_file(session_id)
        if not path.exists():
            return []
        return await asyncio.to_thread(self._read_json, path)

    async def _write_session(self, session_id: str, data: list[dict[str, Any]]) -> None:
        path = self._session_file(session_id)
        await asyncio.to_thread(self._write_json, path, data)

    @staticmethod
    def _read_json(path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _write_json(path: Path, data: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)

    def _dict_to_document(self, document_data: dict[str, Any]) -> SessionDocument:
        return SessionDocument(
            filename=document_data["filename"],
            chunks=document_data["chunks"],
            resource_type=document_data["resource_type"],
            metadata=document_data.get("metadata", {}),
        )

    async def add(
        self,
        session_id: str,
        filename: str,
        chunks: list[str],
        resource_type: str,
        metadata: dict[str, Any],
    ) -> None:
        documents = await self._read_session(session_id)
        documents = [doc for doc in documents if doc.get("filename") != filename]
        documents.append({
            "filename": filename,
            "chunks": chunks,
            "resource_type": resource_type,
            "metadata": metadata,
        })
        await self._write_session(session_id, documents)

    async def list(self, session_id: str) -> list[SessionDocument]:
        documents = await self._read_session(session_id)
        return [self._dict_to_document(doc) for doc in documents]

    async def remove(self, session_id: str, filename: str) -> None:
        documents = await self._read_session(session_id)
        documents = [doc for doc in documents if doc.get("filename") != filename]
        await self._write_session(session_id, documents)

    async def format_context(self, session_id: str) -> str:
        documents = await self.list(session_id)
        chunks: list[str] = []
        for document in documents:
            chunks.extend(document.chunks)
        return "\n".join(chunks)
