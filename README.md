---
title: ADE-Bot
emoji: 🏗️
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# ADE-Bot

Chatbot institucional para el Área de Ingeniería en Diseño. Responde consultas sobre pensum, trámites, licitaciones, normativas y finanzas usando recuperación semántica sobre documentos oficiales del área.

---

## Estructura del proyecto

```
ADE-Bot Project/
├── main.py               — Servidor FastAPI + endpoints REST
├── services/
│   └── chat_service.py   — Lógica central: RAG + prompt + log
├── infrastructure/
│   ├── llm_client.py     — Cliente Gemini (LangChain)
│   ├── vector_store.py   — ChromaDB con embeddings de Google
│   └── log_repository.py — Registro de consultas en SQLite
├── ingesta/
│   └── ingest.py         — Pipeline offline: PDF → ChromaDB
├── tests/
│   └── banco_preguntas.py — Banco de pruebas Módulo 4
├── static/
│   └── index.html        — Interfaz web (chat + visor 3D)
├── datos/                — Carpeta para los PDFs fuente
├── db/                   — ChromaDB + SQLite (generados)
└── docs/
    ├── arquitectura.md   — Diagramas de arquitectura
    ├── api.md            — Referencia de endpoints REST
    └── guia_pruebas.md   — Guía de pruebas y criterio ≥ 90%
```

---

## Requisitos

- Python 3.11+
- Clave de API de Google Gemini (`GEMINI_API_KEY`)

---

## Instalación

```bash
# 1. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
copy .env.example .env
# Editar .env y pegar la clave GEMINI_API_KEY
```

---

## Configuración (`.env`)

| Variable              | Descripción                                    | Default                    |
|-----------------------|------------------------------------------------|----------------------------|
| `GROQ_API_KEY`        | Clave de la API de Groq *(prioridad sobre Gemini)* | —                      |
| `GROQ_MODEL`          | Modelo Groq a usar                             | `llama-3.3-70b-versatile`  |
| `GEMINI_API_KEY`      | Clave de la API de Google Gemini               | —                          |
| `GEMINI_MODEL`        | Modelo Gemini a usar                           | `gemini-2.5-pro`           |
| `CHROMA_PATH`         | Ruta de la base vectorial ChromaDB             | `./db/chroma`              |
| `SQLITE_PATH`         | Ruta del archivo de logs SQLite                | `./db/logs.db`             |
| `TOP_K`               | Fragmentos máximos a recuperar por consulta    | `4`                        |
| `SIMILARITY_THRESHOLD`| Puntuación mínima de similitud semántica       | `0.75`                     |

> El servidor usa Groq si `GROQ_API_KEY` está definida; de lo contrario usa Gemini. Basta con quitar o comentar `GROQ_API_KEY` en `.env` para volver a Gemini.

---

## Ingesta de documentos

Antes de usar el chat, los PDFs deben indexarse en ChromaDB. Coloca los archivos en la carpeta `datos/` y ejecuta:

```bash
python -m ingesta.ingest
```

El script detecta automáticamente el tema de cada documento según su nombre:

| Palabra clave en nombre | Tema asignado              |
|-------------------------|----------------------------|
| `pensum`                | Pensum y materias          |
| `licitacion`            | Licitaciones y contratos   |
| `proceso`               | Trámites administrativos   |
| `plano`                 | Normas de diseño           |
| `financiero`            | Presupuesto y finanzas     |
| `seguridad`             | Seguridad en obras         |
| *(cualquier otro)*      | General                    |

---

## Ejecutar el servidor

```bash
python main.py
```

O con recarga automática en desarrollo:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

La interfaz web queda disponible en `http://localhost:8000`.

---

## Interfaz web

La interfaz (`static/index.html`) incluye:

- **Panel de chat** — conversaciones múltiples con historial en la barra lateral
- **Visor 3D** — modelos Sketchfab de 14 materiales de ingeniería, activados automáticamente cuando el usuario menciona un material en la consulta
- **Subir PDF** — adjunta un documento a la sesión activa para ampliar el contexto del bot
- **Historial** — las últimas sesiones se guardan en `localStorage`

---

## Banco de pruebas (Módulo 4)

```bash
python -m tests.banco_preguntas
```

Evalúa 12 consultas (8 institucionales + 4 fuera de alcance). El criterio de aprobación es **≥ 90 %** de precisión. Ver `docs/guia_pruebas.md` para detalles.

---

## Equipo

| Módulo | Responsable      | Área                              |
|--------|------------------|-----------------------------------|
| 1      | Luis Millán      | Base de conocimientos             |
| 2      | Arnaldo Perdomo  | IA y PLN                          |
| 3      | Yvanna Bravo     | Interfaz web                      |
| 4      | Keibel Guilarte  | Pruebas y control de calidad      |
| 5      | Alejandro Duarte | Infraestructura y soporte         |
