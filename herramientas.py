from dataclasses import dataclass

from langchain.tools import ToolRuntime, tool
from dominio import ServicioBiblioteca, ErrorDeNegocio, cargar_servicio  # noqa: F401  (contrato)

ESCENARIO = "biblioteca"


@dataclass
class Contexto:
    """Lo que el agente le pasa a cada herramienta en cada invocación (no lo ve el modelo)."""
    servicio: ServicioBiblioteca


@tool
def buscar_libro(query: str, runtime: ToolRuntime[Contexto]) -> str:
    """Busca libros en el catálogo por título o autor. Retorna la lista de libros encontrados."""
    return str(runtime.context.servicio.buscar_libro(query))


@tool
def consultar_prestamos(usuario_id: str, runtime: ToolRuntime[Contexto]) -> str:
    """Consulta los préstamos activos e históricos de un usuario específico dado su usuario_id."""
    return str(runtime.context.servicio.obtener_prestamos_usuario(usuario_id))


@tool
def registrar_prestamo(usuario_id: str, libro_id: str, runtime: ToolRuntime[Contexto]) -> str:
    """Registra el préstamo de un libro para un usuario. Requiere aprobación previa."""
    try:
        resultado = runtime.context.servicio.registrar_prestamo(usuario_id, libro_id)
        return f"Éxito: Préstamo registrado correctamente -> {resultado}"
    except ErrorDeNegocio as e:
        return f"RECHAZADO POR DOMINIO: {str(e)}"


@tool
def procesar_devolucion(prestamo_id: str, runtime: ToolRuntime[Contexto]) -> str:
    """Procesa la devolución de un libro dado su prestamo_id. Requiere aprobación previa."""
    try:
        resultado = runtime.context.servicio.procesar_devolucion(prestamo_id)
        return f"Éxito: Devolución procesada correctamente -> {resultado}"
    except ErrorDeNegocio as e:
        return f"RECHAZADO POR DOMINIO: {str(e)}"


@tool
def renovar_prestamo(prestamo_id: str, runtime: ToolRuntime[Contexto]) -> str:
    """Solicita la renovación de un préstamo activo por 7 días adicionales. Requiere aprobación previa."""
    try:
        resultado = runtime.context.servicio.renovar_prestamo(prestamo_id)
        return f"Éxito: Préstamo renovado correctamente -> {resultado}"
    except ErrorDeNegocio as e:
        return f"RECHAZADO POR DOMINIO: {str(e)}"


HERRAMIENTAS = [buscar_libro, consultar_prestamos, registrar_prestamo, procesar_devolucion, renovar_prestamo]
