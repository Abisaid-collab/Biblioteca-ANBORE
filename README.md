# Biblioteca-ANBORE — Agente LangChain (Parcial 2, Equipo ANBORE)

Asistente conversacional para la atención automatizada de una **biblioteca**: búsqueda en el catálogo, consulta, registro, renovación y devolución de préstamos. Usa **LangChain**, **LangGraph** y **Groq** (`openai/gpt-oss-120b`).

> El enunciado pedía `llama-3.3-70b-versatile`, pero Groq ya no lo ofrece (responde `404 model_not_found`). Se usa `openai/gpt-oss-120b`, el modelo más grande disponible con soporte para llamar herramientas. Ver [`reflexion.md`](reflexion.md).

## Integrantes

| Nombre | Matrícula |
|--------|-----------|
| Abisaid Guadalupe Angulo Munguia | 24040115 |
| Edgar Gael Reyes Quevedo | 24040158 |
| Eduardo Borquez Navarrete | 24040446 |

## Escenario

La biblioteca opera con una fecha fija (`fecha_hoy = 2025-11-20`) y un pequeño catálogo en `datos.json`. El LLM **solo orquesta** la conversación; todas las reglas (multas, límite de préstamos, stock, renovaciones) se validan en `dominio.py`. Cada operación de escritura necesita la **aprobación explícita** del bibliotecario (Human-In-The-Loop). Las reglas completas están en [`REGLAS.md`](REGLAS.md).

## Arquitectura (3 capas, KISS)

```
Usuario ──► agente.py ──► herramientas.py ──► dominio.py ──► datos.json
           (LLM + HITL)   (@tool, try/except)  (reglas, ErrorDeNegocio)
```

| Archivo | Responsabilidad |
|---------|-----------------|
| `dominio.py` | Funciones puras sobre el JSON. Lanza `ErrorDeNegocio` si se viola una regla. |
| `herramientas.py` | Envuelve cada método del dominio en una `@tool` (1:1) y convierte `ErrorDeNegocio` en `"RECHAZADO POR DOMINIO: ..."`. |
| `agente.py` | Prompt, modelo Groq, checkpointer (`MemorySaver`) y HITL (`HumanInTheLoopMiddleware`). Incluye un chat por consola. |

## Guía de ejecución

### Forma rápida (recomendada)

Requisito: tener instalado [Python 3.10+](https://www.python.org/downloads/).

- **Windows:** doble clic en `iniciar.bat`.
- **macOS / Linux:** `bash iniciar.sh`.

La primera vez el lanzador crea el entorno e instala las dependencias (1 o 2 minutos). Después abre el chat con el agente. Si no encuentra `.env`, pide la `GROQ_API_KEY` y la guarda.

### Forma manual

Requisitos: Python 3.10+ y una clave de [Groq](https://console.groq.com/keys).

```bash
# 1. Entorno virtual y dependencias
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Clave de API (nunca va en el código; .env está en .gitignore)
copy .env.example .env          # Linux/macOS: cp .env.example .env
#    y edita .env con tu GROQ_API_KEY

# 3. Conversar con el agente
python agente.py

# 4. Pruebas
pytest pruebas -v
```

Durante la conversación, cuando el agente intenta registrar, renovar o devolver un préstamo, la consola pregunta:

```
[APROBACIÓN] ¿Ejecutar registrar_prestamo({'usuario_id': 'USR-101', 'libro_id': 'LIB-001'})? [s/n]:
```

Con `s` la operación se ejecuta (y el dominio aún puede rechazarla). Con `n` no se modifica nada.

## Entrega en .zip y seguridad

Hay dos formas de distribuir el proyecto:

| | GitHub | `parcial2-ANBORE.zip` (entrega) |
|---|---|---|
| `.env` con `GROQ_API_KEY` | **No** (excluido en `.gitignore`) | **Sí**, para que el evaluador ejecute `iniciar.bat` sin configurar nada |
| `.venv/`, `__pycache__/`, `.pytest_cache/` | No | No (el lanzador los regenera) |

- **La clave nunca está en el código fuente:** `agente.py` la lee con `os.getenv("GROQ_API_KEY")`, y una prueba revisa que ningún `.py` contenga una clave.
- **El zip se genera con `git archive`,** así que solo contiene archivos versionados más el `.env`. Ningún archivo local se cuela por accidente.
- **La clave de la entrega es revocable:** el equipo la desactiva en la consola de Groq cuando termine la evaluación.

Las pruebas (`pytest pruebas`) **no necesitan clave** ni conexión a internet.

## Datos de prueba

| ID | Descripción |
|----|-------------|
| `USR-101` | Ana Gómez, sin multas, con 1 préstamo activo (`PRE-001`, vence 2025-11-22). |
| `USR-102` | Carlos López, multa pendiente de $50.00, así que no puede pedir préstamos. |
| `LIB-001` | *Cien Años de Soledad*, 1 copia disponible. |
| `LIB-002` | *El Algoritmo Definitivo*, 0 copias disponibles. |
