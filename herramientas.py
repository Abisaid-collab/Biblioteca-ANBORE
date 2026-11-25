from pathlib import Path

from langchain_core.tools import tool
from dominio import ServicioBiblioteca, ErrorDeNegocio

# Ruta absoluta a datos.json para que funcione sin importar desde dónde se ejecute.
servicio = ServicioBiblioteca(Path(__file__).parent / "datos.json")


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
