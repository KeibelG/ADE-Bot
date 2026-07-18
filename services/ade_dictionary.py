import re
from typing import Iterable

from services.ade_taxonomy import (
    ADE_SYNONYMS,
    find_role_terms,
    is_ade_term,
    normalize_text,
    resolve_synonyms,
)

ADE_BLOCKLIST_TERMS = {
    "medicina", "hospital", "derecho penal", "abogado", "psicología", "psicologia",
    "software", "hardware", "informática", "informatica", "biología", "biologia", "salud",
    "farmacia", "enfermería", "nutricion", "nutrición", "marketing", "ventas",
    "redes sociales", "publicidad", "diseño gráfico", "grafico", "nutrición deportiva",
}

REJECT_MESSAGE = (
    "Lo siento, soy Juanito el Inge y solo puedo responder preguntas relacionadas con "
    "Administración, Diseño e Ingeniería (ADE) de la UNEG. "
    "Por favor, formula tu consulta en ese ámbito."
)

_WORD_RE = re.compile(r"\b[\wáéíóúñÑÁÉÍÓÚüÜ]+\b", flags=re.IGNORECASE)


def _has_any(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def texto_fuera_de_alcance(texto: str) -> bool:
    normalized = resolve_synonyms(texto)
    return _has_any(normalized, ADE_BLOCKLIST_TERMS)


def get_role_matches(texto: str) -> list[str]:
    normalized = resolve_synonyms(texto)
    return find_role_terms(normalized)


def get_synonym_matches(texto: str) -> list[str]:
    normalized = resolve_synonyms(texto)
    return [alias for alias, canonical in ADE_SYNONYMS.items() if canonical in normalized]


def texto_es_ade(texto: str) -> bool:
    if not texto or not texto.strip():
        return False

    normalized = resolve_synonyms(texto)
    if texto_fuera_de_alcance(normalized):
        return False

    return is_ade_term(normalized)
