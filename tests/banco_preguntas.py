import asyncio

from infrastructure.vector_store import VectorStore
from infrastructure.llm_client import LLMClient
from infrastructure.log_repository import LogRepository
from services.chat_service import ChatService


class _FakeVectorStore(VectorStore):
    def __init__(self, fragmentos: list[str]):
        self._fragmentos = fragmentos

    async def buscar(self, consulta: str, top_k: int, threshold: float) -> list[str]:
        return self._fragmentos


class _FakeLLMClient(LLMClient):
    def __init__(self, respuesta: str):
        self._respuesta = respuesta

    async def generar(self, prompt: str) -> str:
        return self._respuesta


class _FakeLogRepository(LogRepository):
    def __init__(self):
        self.registros: list[dict] = []

    async def guardar(self, user_id: int, consulta: str, respuesta: str | None, resuelta: bool) -> None:
        self.registros.append({
            "user_id": user_id,
            "consulta": consulta,
            "respuesta": respuesta,
            "resuelta": resuelta,
        })


# (consulta, debe_ser_resuelta)
# True  = el bot debe encontrar contexto y responder
# False = el bot debe reconocer que esta fuera de su alcance

BANCO = [
    ("oye cuantos creditos tiene estructuras",    True),
    ("pa pedir un permiso que hago",              True),
    ("que necesito pa inscribir la materia",      True),
    ("que vaina necesito pa la licitacion",       True),
    ("el blueprint ese como se llama",            True),
    ("reglamento de las obras",                   True),
    ("informacion del area",                      True),
    ("cuanto cuesta el tramite",                  True),
    ("ayudame con mi tesis",                      False),
    ("cual es la capital de venezuela",           False),
    ("como programo en python",                   False),
    ("dimelo en ingles",                          False),
]


async def _evaluar(consulta: str, debe_resolver: bool) -> bool:
    fragmentos = ["fragmento institucional de prueba"] if debe_resolver else []
    logs = _FakeLogRepository()

    servicio = ChatService(
        vector_store=_FakeVectorStore(fragmentos),
        llm_client=_FakeLLMClient("respuesta de prueba"),
        log_repository=logs,
    )

    await servicio.procesar_consulta(consulta, user_id=0)
    return logs.registros[0]["resuelta"] == debe_resolver


async def ejecutar_banco() -> None:
    aprobadas = 0
    fallidas = []

    for consulta, debe_resolver in BANCO:
        ok = await _evaluar(consulta, debe_resolver)
        if ok:
            aprobadas += 1
        else:
            fallidas.append((consulta, debe_resolver))

    total = len(BANCO)
    precision = (aprobadas / total) * 100

    print("\n--- Resultado del banco de pruebas ---")
    print(f"Aprobadas : {aprobadas}/{total}")
    print(f"Precision : {precision:.1f}%")
    print(f"Criterio  : >= 90%")
    print(f"Estado    : {'APROBADO' if precision >= 90 else 'RECHAZADO'}")

    if fallidas:
        print("\nPreguntas fallidas:")
        for consulta, esperado in fallidas:
            print(f"  - '{consulta}' (esperado: {'resolver' if esperado else 'rechazar'})")


if __name__ == "__main__":
    asyncio.run(ejecutar_banco())
