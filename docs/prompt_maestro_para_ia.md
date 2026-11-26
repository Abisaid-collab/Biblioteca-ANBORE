# Prompt Maestro: Construcción del Agente LangChain - Escenario Biblioteca

## 🎯 Objetivo General

Actúa como un Desarrollador Senior de Inteligencia Artificial y Python. Tu tarea es construir un sistema multi-capa completo en Python utilizando **LangChain**, **LangGraph** y la API de **Groq** (`llama-3.3-70b-versatile`) para gestionar la atención automatizada de una **Biblioteca**.

El sistema debe cumplir estrictamente con los siguientes pilares:

1. **Principio KISS (Keep It Simple, Stupid)**: Mantén el diseño y el código simples, legibles y directos. Evita la sobreingeniería, las capas innecesarias de abstracción y la complejidad redundante. El código debe ser tan claro que cualquier integrante del equipo pueda explicarlo fácilmente.

2. **Desacoplamiento total**: El LLM es solo un orquestador de la conversación. Las reglas del negocio se validan exclusivamente en `dominio.py`.

3. **Seguridad e Inviolabilidad**: Las violaciones de reglas lanzan `ErrorDeNegocio`. Ninguna clave de API debe exponerse en el código fuente.

4. **Human-In-The-Loop (HITL)**: Toda herramienta de escritura requiere aprobación humana explícita antes de ejecutar la mutación.

5. **Respeto al Contrato**: Firmas de funciones, nombres de archivos y estructuras de retorno no se pueden alterar.

## 🧱 Aplicación del Principio KISS en el Proyecto

* **Dominio simple**: Funciones puras de Python que operan directamente sobre diccionarios y listas simples del JSON, sin modelos ORM complejos ni clases innecesarias.
* **Herramientas directas**: Mapeo 1:1 de métodos del dominio a herramientas `@tool`, con un bloque `try/except` limpio y mensajes de retorno en texto plano.
* **Prompt claro y conciso**: Instrucciones directas al LLM sin reglas ocultas ni lógica condicional compleja en el texto.
* **Mantenibilidad**: Código limpio que facilite la resolución de casos borde y la preparación para el cuestionario individual.

## 📁 Estructura del Proyecto

```
parcial2-equipo-07/
├── .env                    # (Excluido de Git, contiene GROQ_API_KEY)
├── README.md               # Integrantes, escenario y guía de ejecución
├── reflexion.md            # Análisis técnico y aprendizaje del equipo
├── conversaciones.md       # 4 conversaciones reales de evidencia
├── REGLAS.md               # Especificación de reglas de negocio
├── datos.json              # Estado de la base de datos local y fecha fija
├── dominio.py              # Lógica pura del dominio (Lanza ErrorDeNegocio - KISS)
├── herramientas.py         # Decoradores @tool de LangChain (Capturan ErrorDeNegocio)
├── agente.py               # Prompt, modelo Groq, checkpointer y HITL
└── pruebas/
    ├── conftest.py
    ├── test_publicos.py    # (Inalterable)
    └── test_equipo.py      # Pruebas unitarias de las reglas de negocio
```

## 📋 Especificaciones por Archivo

### 1. `REGLAS.md` (Reglas de Negocio de la Biblioteca)

Define explícitamente las siguientes reglas simples:

* **Fecha del Sistema**: Operar **únicamente** con la variable `fecha_hoy` presente en `datos.json`. Queda prohibido el uso de `datetime.date.today()`.
* **Préstamos**:
  * Un usuario suspendido o con multas pendientes (`multa_pendiente > 0`) **no puede** pedir préstamos.
  * El usuario no puede exceder el límite de 3 préstamos activos simultáneos.
  * No se puede prestar un libro si `copias_disponibles <= 0`.
  * La fecha de vencimiento por defecto es de 7 días naturales a partir de `fecha_hoy`.
* **Devoluciones**:
  * Al devolver un libro a tiempo, `copias_disponibles` aumenta en 1 y el préstamo pasa a estado `"devuelto"`.
  * Si `fecha_hoy > fecha_vencimiento`, se genera una multa de **$10.00 MXN por cada día de retraso**, asignándose a `multa_pendiente` del usuario.
* **Renovaciones**:
  * Solo se puede renovar un préstamo en estado `"activo"`.
  * No se puede renovar un préstamo si ya está vencido (`fecha_hoy > fecha_vencimiento`).
  * Cada préstamo permite un máximo de 1 renovación (extiende la fecha 7 días más).

### 2. `datos.json` (Semilla de Datos)

```json
{
  "fecha_hoy": "2025-11-20",
  "libros": [
    {
      "id": "LIB-001",
      "titulo": "Cien Años de Soledad",
      "autor": "Gabriel García Márquez",
      "ejemplares_totales": 3,
      "copias_disponibles": 1
    },
    {
      "id": "LIB-002",
      "titulo": "El Algoritmo Definitivo",
      "autor": "Pedro Domingos",
      "ejemplares_totales": 2,
      "copias_disponibles": 0
    }
  ],
  "usuarios": [
    {
      "id": "USR-101",
      "nombre": "Ana Gómez",
      "estado": "activo",
      "multa_pendiente": 0.0
    },
    {
      "id": "USR-102",
      "nombre": "Carlos López",
      "estado": "activo",
      "multa_pendiente": 50.0
    }
  ],
  "prestamos": [
    {
      "id": "PRE-001",
      "usuario_id": "USR-101",
      "libro_id": "LIB-001",
      "fecha_prestamo": "2025-11-15",
      "fecha_vencimiento": "2025-11-22",
      "renovaciones": 0,
      "estado": "activo"
    }
  ]
}
```

### 3. `dominio.py` (Capa de Negocio - Enfoque KISS)

```python
import json
from datetime import datetime, timedelta

class ErrorDeNegocio(Exception):
    """Excepción para violaciones de reglas de la biblioteca."""
    pass

class ServicioBiblioteca:
    def __init__(self, ruta_datos="datos.json"):
        self.ruta_datos = ruta_datos
        self.cargar_datos()

    def cargar_datos(self):
        with open(self.ruta_datos, "r", encoding="utf-8") as f:
            self.datos = json.load(f)
        self.hoy = datetime.strptime(self.datos["fecha_hoy"], "%Y-%m-%d").date()

    def buscar_libro(self, titulo_o_autor: str) -> list[dict]:
        query = titulo_o_autor.lower()
        return [
            l for l in self.datos["libros"]
            if query in l["titulo"].lower() or query in l["autor"].lower()
        ]

    def obtener_prestamos_usuario(self, usuario_id: str) -> list[dict]:
        return [p for p in self.datos["prestamos"] if p["usuario_id"] == usuario_id]

    def registrar_prestamo(self, usuario_id: str, libro_id: str) -> dict:
        usuario = next((u for u in self.datos["usuarios"] if u["id"] == usuario_id), None)
        if not usuario:
            raise ErrorDeNegocio(f"El usuario '{usuario_id}' no existe.")
        if usuario["multa_pendiente"] > 0:
            raise ErrorDeNegocio(f"El usuario {usuario['nombre']} tiene una multa pendiente de ${usuario['multa_pendiente']}.")
        
        prestamos_activos = [p for p in self.datos["prestamos"] if p["usuario_id"] == usuario_id and p["estado"] == "activo"]
        if len(prestamos_activos) >= 3:
            raise ErrorDeNegocio("El usuario ha alcanzado el límite máximo de 3 préstamos activos.")

        libro = next((l for l in self.datos["libros"] if l["id"] == libro_id), None)
        if not libro:
            raise ErrorDeNegocio(f"El libro '{libro_id}' no existe.")
        if libro["copias_disponibles"] <= 0:
            raise ErrorDeNegocio(f"El libro '{libro['titulo']}' no tiene copias disponibles.")

        # Mutación simple
        libro["copias_disponibles"] -= 1
        fecha_vencimiento = self.hoy + timedelta(days=7)
        nuevo_prestamo = {
            "id": f"PRE-00{len(self.datos['prestamos']) + 1}",
            "usuario_id": usuario_id,
            "libro_id": libro_id,
            "fecha_prestamo": self.hoy.strftime("%Y-%m-%d"),
            "fecha_vencimiento": fecha_vencimiento.strftime("%Y-%m-%d"),
            "renovaciones": 0,
            "estado": "activo"
        }
        self.datos["prestamos"].append(nuevo_prestamo)
        return nuevo_prestamo

    def procesar_devolucion(self, prestamo_id: str) -> dict:
        prestamo = next((p for p in self.datos["prestamos"] if p["id"] == prestamo_id), None)
        if not prestamo or prestamo["estado"] != "activo":
            raise ErrorDeNegocio(f"El préstamo '{prestamo_id}' no está activo o no existe.")

        fecha_venc = datetime.strptime(prestamo["fecha_vencimiento"], "%Y-%m-%d").date()
        multa = 0.0
        if self.hoy > fecha_venc:
            dias_retraso = (self.hoy - fecha_venc).days
            multa = dias_retraso * 10.0
            usuario = next(u for u in self.datos["usuarios"] if u["id"] == prestamo["usuario_id"])
            usuario["multa_pendiente"] += multa

        libro = next(l for l in self.datos["libros"] if l["id"] == prestamo["libro_id"])
        libro["copias_disponibles"] += 1
        prestamo["estado"] = "devuelto"

        return {"prestamo_id": prestamo_id, "multa_generada": multa, "estado": "devuelto"}

    def renovar_prestamo(self, prestamo_id: str) -> dict:
        prestamo = next((p for p in self.datos["prestamos"] if p["id"] == prestamo_id), None)
        if not prestamo or prestamo["estado"] != "activo":
            raise ErrorDeNegocio(f"El préstamo '{prestamo_id}' no existe o no está activo.")

        fecha_venc = datetime.strptime(prestamo["fecha_vencimiento"], "%Y-%m-%d").date()
        if self.hoy > fecha_venc:
            raise ErrorDeNegocio("No se puede renovar un préstamo que ya está vencido.")
        if prestamo["renovaciones"] >= 1:
            raise ErrorDeNegocio("El préstamo ya alcanzó el número máximo de renovaciones (1).")

        nueva_fecha = fecha_venc + timedelta(days=7)
        prestamo["fecha_vencimiento"] = nueva_fecha.strftime("%Y-%m-%d")
        prestamo["renovaciones"] += 1
        return prestamo
```

### 4. `herramientas.py` (Herramientas LangChain - Implementación Limpia)

```python
from langchain_core.tools import tool
from dominio import ServicioBiblioteca, ErrorDeNegocio

servicio = ServicioBiblioteca()

@tool
def buscar_libro(query: str) -> str:
    """Busca libros en el catálogo por título o autor. Retorna la lista de libros encontrados."""
    return str(servicio.buscar_libro(query))

@tool
def consultar_prestamos(usuario_id: str) -> str:
    """Consulta los préstamos activos e históricos de un usuario específico dado su usuario_id."""
    return str(servicio.obtener_prestamos_usuario(usuario_id))

@tool
def registrar_prestamo(usuario_id: str, libro_id: str) -> str:
    """Registra el préstamo de un libro para un usuario. Requiere aprobación previa."""
    try:
        resultado = servicio.registrar_prestamo(usuario_id, libro_id)
        return f"Éxito: Préstamo registrado correctamente -> {resultado}"
    except ErrorDeNegocio as e:
        return f"RECHAZADO POR DOMINIO: {str(e)}"

@tool
def procesar_devolucion(prestamo_id: str) -> str:
    """Procesa la devolución de un libro dado su prestamo_id. Requiere aprobación previa."""
    try:
        resultado = servicio.procesar_devolucion(prestamo_id)
        return f"Éxito: Devolución procesada correctamente -> {resultado}"
    except ErrorDeNegocio as e:
        return f"RECHAZADO POR DOMINIO: {str(e)}"

@tool
def renovar_prestamo(prestamo_id: str) -> str:
    """Solicita la renovación de un préstamo activo por 7 días adicionales. Requiere aprobación previa."""
    try:
        resultado = servicio.renovar_prestamo(prestamo_id)
        return f"Éxito: Préstamo renovado correctamente -> {resultado}"
    except ErrorDeNegocio as e:
        return f"RECHAZADO POR DOMINIO: {str(e)}"

HERRAMIENTAS = [buscar_libro, consultar_prestamos, registrar_prestamo, procesar_devolucion, renovar_prestamo]
```

### 5. `agente.py` (Agente Groq y Control de Interrupción Simple)

```python
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from herramientas import HERRAMIENTAS

load_dotenv()

PROMPT_SISTEMA = """Eres el asistente virtual principal de la biblioteca.

INSTRUCCIONES CLAVE (Principio KISS):
1. **Dominio**: Atiende únicamente temas de la biblioteca (catálogo, préstamos, renovaciones y devoluciones). Si preguntan algo fuera de este tema, recházalo de forma directa y amable.
2. **Aprobación de Escrituras**: Las herramientas `registrar_prestamo`, `procesar_devolucion` y `renovar_prestamo` son de ESCRITURA. Confirma que tienes los parámetros necesarios antes de invocarlas.
3. **Manejo de Respuestas**: Si la herramienta responde con "RECHAZADO POR DOMINIO", explícale al usuario la razón exacta del rechazo en lenguaje sencillo.
"""

ACCIONES_CON_APROBACION = [
    "registrar_prestamo",
    "procesar_devolucion",
    "renovar_prestamo"
]

def crear_agente(modelo=None, checkpointer=None):
    if modelo is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("No se configuró la variable GROQ_API_KEY en el entorno.")
        modelo = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            groq_api_key=api_key
        )
    
    agente = create_react_agent(
        model=modelo,
        tools=HERRAMIENTAS,
        state_modifier=PROMPT_SISTEMA,
        checkpointer=checkpointer,
        interrupt_before=ACCIONES_CON_APROBACION
    )
    return agente
```

## 🧪 Pruebas Unitarias Simples (`pruebas/test_equipo.py`)

Aplica KISS escribiendo pruebas directas y asertivas:

1. `test_prestamo_usuario_con_multa_falla`: Verifica que un usuario con `multa_pendiente > 0` reciba `ErrorDeNegocio`.
2. `test_prestamo_sin_stock_falla`: Comprueba que solicitar un libro con `copias_disponibles == 0` falle inmediatamente.
3. `test_renovacion_prestamo_vencido_falla`: Verifica que renovar un préstamo vencido sea rechazado.
4. `test_inviolabilidad_estado_ante_error`: Comprueba en 3 líneas que los arrays de datos en `datos.json` no hayan cambiado tras una excepción.

## 🔒 Reglas de Oro

* **Cero API Keys en Código**: `GROQ_API_KEY` siempre se lee mediante `os.getenv()`.
* **KISS en Todo**: Sin código muerto, sin decoradores extras innecesarios, sin lógica duplicada entre prompt y dominio.
* **Interrupción en Escritura**: Validar que `ACCIONES_CON_APROBACION` contenga exactamente las herramientas de mutación.