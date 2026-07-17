import os
import time

from google import genai
from google.genai.errors import ClientError
from langchain.embeddings.base import Embeddings


class GoogleGenAIEmbeddings(Embeddings):
    _MAX_BATCH_SIZE = int(os.getenv("GOOGLE_GENAI_EMBEDDING_BATCH_SIZE", "25"))
    _BATCH_DELAY_SECONDS = float(os.getenv("GOOGLE_GENAI_EMBEDDING_DELAY", "0.2"))

    def __init__(self, api_key: str, model: str = "gemini-embedding-2-preview"):
        if not api_key:
            raise ValueError("Debe proporcionar una API key de Google GenAI para inicializar el cliente.")

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings: list[list[float]] = []
        for start in range(0, len(texts), self._MAX_BATCH_SIZE):
            batch = texts[start : start + self._MAX_BATCH_SIZE]
            try:
                response = self._client.models.embed_content(
                    model=self._model,
                    contents=batch,
                )
            except ClientError as exc:
                raise RuntimeError(
                    f"Error de Google GenAI al generar embeddings con el modelo '{self._model}'. "
                    "Verifique su clave, cuota y configuración de modelo. "
                    f"Mensaje original: {exc}"
                ) from exc

            if not response.embeddings:
                raise ValueError("No se devolvieron embeddings de Google GenAI en el lote.")

            for embedding in response.embeddings:
                if embedding.values is None:
                    raise ValueError("Respuesta de embedding incompleta: valores faltantes.")
                embeddings.append(list(embedding.values))

            time.sleep(self._BATCH_DELAY_SECONDS)

        return embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed_texts(texts)

    def embed_query(self, text: str) -> list[float]:
        resultado = self._embed_texts([text])
        return resultado[0] if resultado else []
