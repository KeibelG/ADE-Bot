from infrastructure.vector_store import VectorStore
from infrastructure.llm_client import LLMClient
from infrastructure.log_repository import LogRepository
from services.ade_dictionary import REJECT_MESSAGE, texto_es_ade

_SALUDOS = {
    "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
    "hey", "ey", "hi", "hello", "que tal", "como estas", "buen dia",
}

_META = {
    "que puedes hacer", "que sabes", "en que me ayudas", "que podria preguntarte",
    "que puedo preguntarte", "ayudame", "para que sirves", "quien eres",
    "como funciona", "que eres",
}


def _es_saludo_o_meta(texto: str) -> bool:
    t = texto.lower().strip().rstrip("?!.")
    return t in _SALUDOS or any(m in t for m in _META)

_SYSTEM_PROMPT = (
    "Eres Juanito el Inge, asistente institucional exclusivo del Área de "
    "Administración, Diseño e Ingeniería (ADE) de la UNEG. "
    "Tu tono es formal, claro y amable. "
    "\n\nREGLAS ESTRICTAS:"
    "\n1. Responde ÚNICAMENTE con información del contexto oficial recuperado. "
    "No inventes ni añadas contenido externo."
    "\n2. Cita cada fuente usada en el formato [Fuente: nombre_archivo.ext]."
    "\n3. Si el contexto incluye documentos ajenos al área ADE (bases de datos, "
    "medicina, derecho, informática general, etc.), IGNÓRALOS completamente "
    "y explica que solo puedes usar documentos del área."
    "\n4. Si la pregunta o los documentos están fuera del alcance ADE y no hay "
    "contexto oficial suficiente, rechaza la consulta con cortesía institucional."
    "\n5. Interpreta jerga estudiantil: 'que vaina' → trámite, "
    "'blueprint' → plano, 'pa pedir un permiso' → procedimiento administrativo."
)


class ChatService:
    def __init__(
        self,
        vector_store: VectorStore,
        llm_client: LLMClient,
        log_repository: LogRepository,
        top_k: int = 4,
        similarity_threshold: float = 0.60,
    ):
        self._vector_store = vector_store
        self._llm = llm_client
        self._logs = log_repository
        self._top_k = top_k
        self._threshold = similarity_threshold

    async def procesar_consulta(
        self,
        texto: str,
        user_id: int,
        contexto_extra: str = "",
    ) -> str:
        consulta_ade = texto_es_ade(texto)
        contexto_validado = ""
        advertencia_sesion = ""

        if contexto_extra:
            if texto_es_ade(contexto_extra):
                contexto_validado = contexto_extra
            else:
                advertencia_sesion = (
                    "\n\n⚠️ Nota: El documento que adjuntaste no parece pertenecer "
                    "al Área de Administración, Diseño e Ingeniería, por lo que fue ignorado."
                )

        if not consulta_ade and not _es_saludo_o_meta(texto):
            respuesta = REJECT_MESSAGE + advertencia_sesion
            await self._logs.guardar(user_id, texto, respuesta, resuelta=False)
            return respuesta

        fragmentos = await self._vector_store.buscar(texto, self._top_k, self._threshold)

        if not fragmentos and not contexto_validado:
            respuesta = (
                "Entiendo tu pregunta dentro del área ADE, pero no tengo documentos oficiales "
                "del área cargados en este momento. Por favor, carga un documento ADE o usa una "
                "sesión con fuentes ADE para que pueda responder con información real."
            )
            await self._logs.guardar(user_id, texto, respuesta, resuelta=False)
            return respuesta

        prompt = self._construir_prompt(texto, fragmentos, contexto_validado)
        try:
            respuesta = await self._llm.generar(prompt)
        except Exception as exc:
            respuesta = (
                "No pude generar la respuesta en este momento. "
                "Intenta de nuevo más tarde."
            )
            await self._logs.guardar(user_id, texto, str(exc), resuelta=False)
            return respuesta + advertencia_sesion

        await self._logs.guardar(user_id, texto, respuesta, resuelta=bool(fragmentos or contexto_validado))
        return respuesta + advertencia_sesion

    def _construir_prompt(
        self,
        consulta: str,
        fragmentos: list[str],
        contexto_extra: str = "",
    ) -> str:
        partes: list[str] = []
        if fragmentos:
            partes.append("Documentos oficiales del área (ChromaDB):\n" + "\n\n".join(fragmentos))
        if contexto_extra:
            partes.append("Documentos ADE cargados en la sesión:\n" + contexto_extra)
        contexto = "\n\n---\n\n".join(partes)
        return (
            f"{_SYSTEM_PROMPT}\n\n"
            f"Contexto:\n{contexto}\n\n"
            f"Pregunta: {consulta}\n"
            f"Respuesta:"
        )
