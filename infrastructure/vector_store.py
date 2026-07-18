import os
from abc import ABC, abstractmethod

from langchain_chroma import Chroma
from infrastructure.google_embeddings import GoogleGenAIEmbeddings
from starlette.concurrency import run_in_threadpool


class VectorStore(ABC):
    @abstractmethod
    async def buscar(self, consulta: str, top_k: int, threshold: float) -> list[str]:
        pass


class ChromaVectorStore(VectorStore):
    def __init__(self, path: str, api_key: str):
        model = os.getenv("GOOGLE_GENAI_EMBEDDING_MODEL", "gemini-embedding-001")
        embeddings = GoogleGenAIEmbeddings(api_key=api_key, model=model)
        self._db = Chroma(persist_directory=path, embedding_function=embeddings)

    async def buscar(self, consulta: str, top_k: int, threshold: float) -> list[str]:
        try:
            resultados = await run_in_threadpool(
                self._db.similarity_search_with_relevance_scores,
                consulta,
                k=top_k,
            )
        except Exception:
            return []

        fragmentos = []
        for doc, score in resultados:
            if score < threshold:
                continue
            fuente = doc.metadata.get("fuente") or doc.metadata.get("source") or "documento"
            fragmentos.append(f"{doc.page_content}\n[Fuente: {fuente}]")
        return fragmentos
