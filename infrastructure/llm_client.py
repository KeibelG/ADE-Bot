import asyncio
from abc import ABC, abstractmethod

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq


from typing import Any

class LLMClient(ABC):
    @abstractmethod
    async def generar(self, prompt: str, media_files: list[dict[str, str]] | None = None) -> str:
        pass


class GeminiLLMClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        self._llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)

    async def generar(self, prompt: str, media_files: list[dict[str, str]] | None = None) -> str:
        try:
            content_list: list[Any] = [{"type": "text", "text": prompt}]
            if media_files:
                for media in media_files:
                    mime = media.get("mime_type", "")
                    data = media.get("data", "")
                    if mime.startswith("image/"):
                        content_list.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{data}"}
                        })
                    elif mime == "application/pdf":
                        content_list.append({
                            "type": "media",
                            "mime_type": "application/pdf",
                            "data": data
                        })
            respuesta = await asyncio.wait_for(
                self._llm.ainvoke([HumanMessage(content=content_list)]),
                timeout=25,
            )
            return str(respuesta.content)
        except asyncio.TimeoutError as exc:
            raise RuntimeError("LLM request timed out") from exc


class GroqLLMClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        self._llm = ChatGroq(model=model, api_key=api_key)

    async def generar(self, prompt: str, media_files: list[dict[str, str]] | None = None) -> str:
        try:
            respuesta = await asyncio.wait_for(
                self._llm.ainvoke([HumanMessage(content=prompt)]),
                timeout=20,
            )
            return str(respuesta.content)
        except asyncio.TimeoutError as exc:
            raise RuntimeError("LLM request timed out") from exc
