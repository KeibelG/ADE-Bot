from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ADETerm:
    name: str
    category: str
    aliases: tuple[str, ...] = ()


# Roles y personalidades del ecosistema ADE.
ADE_ROLES = [
    ADETerm(name="docente", category="role", aliases=("profesor", "profesora", "educador", "educadora")),
    ADETerm(name="estudiante", category="role", aliases=("alumno", "alumna", "aprendiz")),
    ADETerm(name="administrativo", category="role", aliases=("administradora", "secretaria", "secretario", "gestor", "gestora")),
    ADETerm(name="coordinador", category="role", aliases=("gestor", "gestora", "coordinadora", "coordinadora academica", "coordinador academico")),
    ADETerm(name="director", category="role", aliases=("directora", "director academico", "directora academica", "director financiero")),
    ADETerm(name="jefe", category="role", aliases=("jefa", "jefe de departamento", "jefa de departamento")),
    ADETerm(name="ingeniero", category="role", aliases=("ingeniera", "arquitecto", "arquitecta")),
    ADETerm(name="asesor", category="role", aliases=("asesora", "tutor", "tutora")),
    ADETerm(name="funcionario", category="role", aliases=("funcionaria", "representante", "supervisor", "supervisora", "inspector", "inspectora")),
]


# Términos comunes de ADE con sinónimos.
ADE_SYNONYMS = {
    "tramite": "trámite",
    "tramites": "trámites",
    "licitacion": "licitación",
    "licitaciones": "licitaciones",
    "norma tecnica": "norma técnica",
    "normas tecnicas": "normas técnicas",
    "gestion": "gestión",
    "gestiones": "gestión",
    "inversion": "inversión",
    "inversiones": "inversión",
    "autorizacion": "autorización",
    "evaluacion": "evaluación",
    "especificacion tecnica": "especificación técnica",
    "memoria tecnica": "memoria técnica",
    "construccion": "construcción",
    "cimentacion": "cimentación",
    "informática": "informatica",
    "docente universitario": "docente",
    "plan de estudios": "plan de estudio",
    "plan de estudio": "plan de estudio",
}


ADE_CATEGORIES = {
    "area": (
        "ade", "administración", "administracion", "ingeniería", "ingenieria", "diseño", "diseno",
        "uneg", "universidad", "carrera", "pensum", "materia", "asignatura", "semestre",
        "area", "información", "informacion",
    ),
    "process": (
        "trámite", "tramite", "proceso", "solicitud", "permiso", "autorización", "autorizacion",
        "expediente", "evaluación", "evaluacion", "registro", "acta", "certificación", "certificacion",
    ),
    "construction": (
        "plano", "croquis", "blueprint", "carga estructural", "estructura", "concreto", "acero",
        "material", "obra", "normativa", "norma", "reglamento", "especificación", "especificacion",
        "memoria técnica", "memoria tecnica", "cimentación", "cimentacion", "construcción", "construccion",
    ),
    "finance": (
        "presupuesto", "financiero", "finanzas", "estado financiero", "partida", "ejecución presupuestaria",
        "ejecucion presupuestaria", "contabilidad", "costo", "inversión", "inversion", "gasto",
    ),
    "document": (
        "plan", "manual", "normativa", "formato", "plantilla", "protocolo", "procedimiento", "documento",
        "informe", "guía", "guia", "registro", "acta", "especificación técnica", "especificacion tecnica",
        "resolución", "resolucion", "memorando", "carta", "nota interna",
    ),
}


def normalize_text(text: str) -> str:
    normalized = text.lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def canonicalize_term(term: str) -> str:
    normalized = normalize_text(term).strip()
    return ADE_SYNONYMS.get(normalized, normalized)


def find_role_terms(text: str) -> list[str]:
    normalized = normalize_text(text)
    matches: list[str] = []
    for role in ADE_ROLES:
        if role.name in normalized:
            matches.append(role.name)
        else:
            for alias in role.aliases:
                if alias in normalized:
                    matches.append(role.name)
                    break
    return sorted(set(matches))


def find_category_terms(text: str) -> list[str]:
    normalized = normalize_text(text)
    matches: list[str] = []
    for category, terms in ADE_CATEGORIES.items():
        if any(term in normalized for term in terms):
            matches.append(category)
    return matches


def resolve_synonyms(text: str) -> str:
    normalized = normalize_text(text)
    for alias, canonical in ADE_SYNONYMS.items():
        normalized = normalized.replace(alias, canonical)
    return normalized


def is_ade_term(text: str) -> bool:
    normalized = resolve_synonyms(text)
    if any(term in normalized for term in ADE_SYNONYMS.values()):
        return True
    if any(term in normalized for terms in ADE_CATEGORIES.values() for term in terms):
        return True
    if find_role_terms(normalized):
        return True
    return False
