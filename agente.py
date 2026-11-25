import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
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

# Debe ser explícito: si es ambiguo, el LLM lo confunde con un error del sistema e inventa causas.
MENSAJE_RECHAZO_HUMANO = (
    "El bibliotecario NO aprobó esta operación y no se ejecutó. "
    "No es un error del sistema ni de los datos. Informa al usuario que su solicitud "
    "no fue autorizada y que acuda al mostrador si tiene dudas."
)


def crear_agente(modelo=None, checkpointer=None):
    if modelo is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("No se configuró la variable GROQ_API_KEY en el entorno.")
        modelo = ChatGroq(
            model="openai/gpt-oss-120b",  # llama-3.3-70b-versatile ya no está disponible en Groq
            temperature=0.0,
            groq_api_key=api_key
        )

    # HITL: el middleware pausa el grafo ANTES de ejecutar cualquier herramienta de escritura.
    # Las pausas necesitan un checkpointer para poder reanudar la conversación.
    agente = create_agent(
        model=modelo,
        tools=HERRAMIENTAS,
        system_prompt=PROMPT_SISTEMA,
        checkpointer=checkpointer or MemorySaver(),
        middleware=[HumanInTheLoopMiddleware(interrupt_on={n: True for n in ACCIONES_CON_APROBACION})]
    )
    return agente


def conversar():
    """Chat por consola. El bibliotecario aprueba o rechaza cada escritura."""
    agente = crear_agente()
    config = {"configurable": {"thread_id": "consola"}}
    print("Asistente de la biblioteca (escribe 'salir' para terminar)")

    while (texto := input("\nUsuario: ").strip()).lower() != "salir":
        resultado = agente.invoke({"messages": [("user", texto)]}, config)

        while "__interrupt__" in resultado:
            decisiones = []
            for accion in resultado["__interrupt__"][0].value["action_requests"]:
                respuesta = input(f"\n[APROBACIÓN] ¿Ejecutar {accion['name']}({accion['args']})? [s/n]: ")
                if respuesta.strip().lower() == "s":
                    decisiones.append({"type": "approve"})
                else:
                    decisiones.append({"type": "reject", "message": MENSAJE_RECHAZO_HUMANO})
            resultado = agente.invoke(Command(resume={"decisions": decisiones}), config)

        print("\nAsistente:", resultado["messages"][-1].content)


if __name__ == "__main__":
    conversar()
