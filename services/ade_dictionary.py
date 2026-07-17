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
    # Exenciones para evitar bloquear herramientas de obra, maquinaria o materiales de construcción
    exempt_terms = {
        "concreto", "acero", "cemento", "ladrillo", "arena", "grava", "madera", "asfalto", "yeso",
        "tuberia", "tuberias", "viga", "bloque", "cabilla", "aditivo", "dosificacion", "dosificación",
        "agregados", "retroexcavadora", "excavadora", "grua", "grúa", "mezcladora", "compactadora",
        "cargador", "dumper", "pavimentadora", "motoniveladora", "tractor", "camion", "camión", "maquinaria",
        "pala", "pico", "carretilla", "martillo", "taladro", "sierra", "nivel", "cinta metrica", "cinta métrica",
        "alicate", "planos", "plano", "covenin", "estructural", "construcción", "construccion", "obra", "render", "modelo 3d",
        "software de diseño", "software de diseno", "software cad", "cad", "autocad", "revit", "sketchup",
        "software estructural", "software de ingeniería", "software de ingenieria",
        "salud ocupacional", "seguridad industrial", "seguridad en obra", "seguridad laboral",
    }
    if _has_any(normalized, exempt_terms):
        return False
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
