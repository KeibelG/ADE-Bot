import asyncio
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from langchain_openai import ChatOpenAI
import asyncio


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
                self._llm.ainvoke([HumanMessage(content=content_list)]),
                timeout=60,
            )

            # gemini-3 devuelve el contenido como una lista de bloques estructurados
            # (con metadata extra como 'signature'), no como string plano.
            # Extraemos solo el texto para no mostrar la estructura cruda en el chat.
            contenido = respuesta.content
            if isinstance(contenido, list):
                texto = "".join(
                    bloque.get("text", "")
                    for bloque in contenido
                    if isinstance(bloque, dict) and bloque.get("type") == "text"
                )
                return texto
            return str(contenido)
        except asyncio.TimeoutError as exc:
            raise RuntimeError("LLM request timed out") from exc

class GroqLLMClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        self._llm = ChatGroq(model=model, api_key=api_key)

    async def generar(self, prompt: str) -> str:
        try:
            # Si hay archivos multimedia, estructuramos la petición en formato multimodal
            if media_files:
                content_list: list[Any] = [{"type": "text", "text": prompt}]
                for media in media_files:
                    mime = media.get("mime_type", "")
                    data = media.get("data", "")
                    if mime.startswith("image/"):
                        # Formato estándar de LangChain / OpenAI para Visión
                        content_list.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{data}"}
                        })
                
                mensaje = HumanMessage(content=content_list)
            else:
                # Si es solo texto plano
                mensaje = HumanMessage(content=prompt)

            respuesta = await asyncio.wait_for(
                self._llm.ainvoke([mensaje]),
                timeout=60,
            )
            return respuesta.content
        except asyncio.TimeoutError as exc:
            raise RuntimeError("LLM request timed out") from exc


class OpenRouterLLMClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        # OpenRouter es 100% compatible con la especificación de OpenAI
        self._llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            max_tokens=2000,
        )

    async def generar(self, prompt: str, media_files: list[dict[str, str]] | None = None) -> str:
        try:
            # Iniciamos el contenido con el texto del prompt del usuario
            content_list = [{"type": "text", "text": prompt}]
            
            # Procesamos archivos multimedia si están presentes en la petición
            if media_files:
                for media in media_files:
                    mime = media.get("mime_type", "")
                    data = media.get("data", "")
                    
                    if not mime or not data:
                        continue
                        
                    # 1. Soporte para imágenes (PNG, JPEG, etc.)
                    if mime.startswith("image/"):
                        content_list.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{data}"
                            }
                        })
                    
                    # 2. Soporte para documentos PDF nativos en OpenRouter (usando Gemini)
                    elif mime == "application/pdf":
                        content_list.append({
                            "type": "image_url", # Los endpoints de OpenAI/OpenRouter reciben los archivos estructurados de esta forma para multimodalidad
                            "image_url": {
                                "url": f"data:{mime};base64,{data}"
                            }
                        })
            
            # Enviamos la petición multimodal
            respuesta = await asyncio.wait_for(
                self._llm.ainvoke([HumanMessage(content=content_list)]),
                timeout=80,  # Damos un margen de tiempo más amplio por el procesamiento de archivos
            )
            return str(respuesta.content)
            
        except asyncio.TimeoutError as exc:
            raise RuntimeError("La solicitud a OpenRouter excedió el tiempo de espera") from exc
        except Exception as exc:
            raise RuntimeError(f"Error en OpenRouter: {str(exc)}") from exc