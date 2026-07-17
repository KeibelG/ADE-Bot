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

_REVISOR_PLANOS_SYSTEM_PROMPT = (
    "Eres Juanito el Inge, asistente técnico experto en revisión de planos del Área de "
    "Administración, Diseño e Ingeniería (ADE) de la UNEG. "
    "Tu tono es formal, claro y amable. "
    "\n\nREGLAS DE REVISIÓN:"
    "\n1. Analiza con detalle el plano, imagen o PDF técnico adjunto en los archivos multimedia."
    "\n2. Identifica posibles inconsistencias estructurales, distribución de espacios y problemas constructivos."
    "\n3. Verifica el cumplimiento de las normativas de construcción aplicables, especialmente las normas COVENIN (como COVENIN 3476-1999 u otras normas técnicas presentes en la carpeta 'datos')."
    "\n4. Cita cada fuente usada en el formato [Fuente: nombre_archivo.ext]."
    "\n5. Proporciona recomendaciones técnicas claras, estructuradas y precisas para la mejora del diseño o plano."
)


class ChatService:
    def __init__(
        self,
        vector_store: VectorStore,
        llm_client: LLMClient,
        log_repository: LogRepository,
        top_k: int = 4,
        similarity_threshold: float = 0.60,
        multimodal_llm_client: LLMClient | None = None,
    ):
        self._vector_store = vector_store
        self._llm = llm_client
        self._logs = log_repository
        self._top_k = top_k
        self._threshold = similarity_threshold
        self._multimodal_llm = multimodal_llm_client or llm_client

    async def procesar_consulta(
        self,
        texto: str,
        user_id: int,
        contexto_extra: str = "",
        media_files: list[dict[str, str]] | None = None,
    ) -> str:
        consulta_ade = texto_es_ade(texto)
        contexto_validado = ""
        advertencia_sesion = ""
        es_multimodal = bool(media_files)

        if contexto_extra:
            if texto_es_ade(contexto_extra):
                contexto_validado = contexto_extra
            else:
                advertencia_sesion = (
                    "\n\n⚠️ Nota: El documento que adjuntaste no parece pertenecer "
                    "al Área de Administración, Diseño e Ingeniería, por lo que fue ignorado."
                )

        # Si la consulta no es ADE, ni es un saludo/meta, ni tiene archivos multimedia, la rechazamos
        if not consulta_ade and not _es_saludo_o_meta(texto) and not es_multimodal:
            respuesta = REJECT_MESSAGE + advertencia_sesion
            await self._logs.guardar(user_id, texto, respuesta, resuelta=False)
            return respuesta

        # RAG: Si se detectan entidades de materiales, maquinaria o herramientas, priorizamos fragmentos relacionados
        priorizar = False
        terms_priorizar = {"material", "maquinaria", "herramienta", "concreto", "acero", "cemento", "retroexcavadora", "covenin", "norma", "obra"}
        if any(term in texto.lower() for term in terms_priorizar):
            priorizar = True

        buscar_k = self._top_k + 4 if priorizar else self._top_k

        # Buscamos en Chroma DB de manera segura (evita que un fallo de la BD tumbe la conversación)
        try:
            fragmentos = await self._vector_store.buscar(texto, buscar_k, self._threshold)
        except Exception:
            fragmentos = []

        if priorizar and fragmentos:
            def score_fragmento(frag: str) -> int:
                frag_lower = frag.lower()
                score = 0
                if "covenin" in frag_lower:
                    score -= 5
                if "manual" in frag_lower:
                    score -= 4
                if any(t in frag_lower for t in ["concreto", "acero", "cemento", "material", "maquinaria", "herramienta"]):
                    score -= 3
                return score
            fragmentos = sorted(fragmentos, key=score_fragmento)[:self._top_k]
        else:
            fragmentos = fragmentos[:self._top_k] if fragmentos else []

        # Si no hay documentos en ChromaDB ni cargados en sesión, no bloqueamos la conversación:
        # dejamos que el LLM responda con su conocimiento general de ADE (ver _construir_prompt).
        prompt = self._construir_prompt(texto, fragmentos, contexto_validado, es_revisor=es_multimodal)
        client_to_use = self._multimodal_llm if es_multimodal else self._llm

        try:
            respuesta = await client_to_use.generar(prompt, media_files=media_files)
        except Exception as exc:
            print("OCURRIÓ UN ERROR CRÍTICO EN EL LLM:", str(exc))
            respuesta = (
                "No pude generar la respuesta en este momento. "
                "Intenta de nuevo más tarde."
            )
            await self._logs.guardar(user_id, texto, str(exc), resuelta=False)
            return respuesta + advertencia_sesion

        await self._logs.guardar(user_id, texto, respuesta, resuelta=bool(fragmentos or contexto_validado or es_multimodal))
        return respuesta + advertencia_sesion

    def _construir_prompt(
        self,
        consulta: str,
        fragmentos: list[str],
        contexto_extra: str = "",
        es_revisor: bool = False,
    ) -> str:
        partes: list[str] = []
        if fragmentos:
            partes.append("Documentos oficiales del área (ChromaDB):\n" + "\n\n".join(fragmentos))
        if contexto_extra:
            partes.append("Documentos ADE cargados en la sesión:\n" + contexto_extra)

        contexto = (
            "\n\n---\n\n".join(partes)
            if partes
            else (
                "No hay documentos adicionales adjuntos para esta consulta. Responde "
                "utilizando tu conocimiento general de ingeniería en diseño, administración "
                "e ingeniería civil de manera profesional."
            )
        )

        sys_prompt = _REVISOR_PLANOS_SYSTEM_PROMPT if es_revisor else _SYSTEM_PROMPT
        return (
            f"{sys_prompt}\n\n"
            f"Contexto:\n{contexto}\n\n"
            f"Pregunta: {consulta}\n"
            f"Respuesta:"
        )