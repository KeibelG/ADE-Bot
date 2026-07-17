import asyncio
from abc import ABC, abstractmethod

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq


class LLMClient(ABC):
    @abstractmethod
    async def generar(self, prompt: str) -> str:
        pass


class GeminiLLMClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        self._llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)

    async def generar(self, prompt: str) -> str:
        try:
            respuesta = await asyncio.wait_for(
                self._llm.ainvoke([HumanMessage(content=prompt)]),
                timeout=20,
            )
            return respuesta.content
        except asyncio.TimeoutError as exc:
            raise RuntimeError("LLM request timed out") from exc


class GroqLLMClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        self._llm = ChatGroq(model=model, api_key=api_key)

    async def generar(self, prompt: str) -> str:
        try:
            respuesta = await asyncio.wait_for(
                self._llm.ainvoke([HumanMessage(content=prompt)]),
                timeout=20,
            )
            return respuesta.content
        except asyncio.TimeoutError as exc:
            raise RuntimeError("LLM request timed out") from exc
