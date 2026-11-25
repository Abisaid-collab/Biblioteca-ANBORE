import copy
import json

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from dominio import ErrorDeNegocio
from agente import ACCIONES_CON_APROBACION, crear_agente


# ---------- Reglas de negocio (dominio.py) ----------

def test_prestamo_usuario_con_multa_falla(servicio):
    with pytest.raises(ErrorDeNegocio, match="multa pendiente"):
        servicio.registrar_prestamo("USR-102", "LIB-001")


def test_prestamo_sin_stock_falla(servicio):
    with pytest.raises(ErrorDeNegocio, match="no tiene copias disponibles"):
        servicio.registrar_prestamo("USR-101", "LIB-002")


def test_renovacion_prestamo_vencido_falla(servicio):
    servicio.hoy = servicio.hoy.replace(day=25)  # PRE-001 vence el 2025-11-22
    with pytest.raises(ErrorDeNegocio, match="vencido"):
        servicio.renovar_prestamo("PRE-001")


def test_inviolabilidad_estado_ante_error(servicio, ruta_datos):
    antes = copy.deepcopy(servicio.datos)
    with pytest.raises(ErrorDeNegocio):
        servicio.registrar_prestamo("USR-102", "LIB-001")
    assert servicio.datos == antes
    assert json.loads(ruta_datos.read_text(encoding="utf-8")) == antes


# ---------- Casos borde adicionales ----------

def test_usuario_suspendido_falla(servicio):
    servicio.datos["usuarios"][0]["estado"] = "suspendido"
    with pytest.raises(ErrorDeNegocio, match="suspendido"):
        servicio.registrar_prestamo("USR-101", "LIB-001")


def test_limite_tres_prestamos_activos(servicio):
    for i in range(2):
        servicio.datos["prestamos"].append({**servicio.datos["prestamos"][0], "id": f"PRE-X{i}"})
    with pytest.raises(ErrorDeNegocio, match="límite máximo de 3"):
        servicio.registrar_prestamo("USR-101", "LIB-001")


def test_prestamo_exitoso_vence_en_7_dias(servicio):
    prestamo = servicio.registrar_prestamo("USR-101", "LIB-001")
    assert prestamo["id"] == "PRE-002"
    assert prestamo["fecha_vencimiento"] == "2025-11-27"
    assert servicio.datos["libros"][0]["copias_disponibles"] == 0


def test_devolucion_tardia_genera_multa(servicio):
    servicio.hoy = servicio.hoy.replace(day=25)  # 3 días de retraso
    resultado = servicio.procesar_devolucion("PRE-001")
    assert resultado["multa_generada"] == 30.0
    assert servicio.datos["usuarios"][0]["multa_pendiente"] == 30.0
    assert servicio.datos["libros"][0]["copias_disponibles"] == 2


def test_solo_una_renovacion(servicio):
    assert servicio.renovar_prestamo("PRE-001")["fecha_vencimiento"] == "2025-11-29"
    with pytest.raises(ErrorDeNegocio, match="máximo de renovaciones"):
        servicio.renovar_prestamo("PRE-001")


# ---------- Human-In-The-Loop (agente.py) ----------

def test_acciones_con_aprobacion_son_las_de_escritura():
    assert set(ACCIONES_CON_APROBACION) == {"registrar_prestamo", "procesar_devolucion", "renovar_prestamo"}


class ModeloFalso(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def test_escritura_se_pausa_hasta_aprobacion():
    llamada = {"name": "registrar_prestamo", "args": {"usuario_id": "USR-101", "libro_id": "LIB-001"}, "id": "1"}
    modelo = ModeloFalso(messages=iter([AIMessage(content="", tool_calls=[llamada])]))
    agente = crear_agente(modelo=modelo)

    resultado = agente.invoke({"messages": [("user", "Presta LIB-001 a USR-101")]}, {"configurable": {"thread_id": "t"}})

    assert "__interrupt__" in resultado
    assert resultado["__interrupt__"][0].value["action_requests"][0]["name"] == "registrar_prestamo"


def test_escritura_rechazada_no_modifica_datos():
    from langgraph.types import Command
    from herramientas import servicio

    llamada = {"name": "registrar_prestamo", "args": {"usuario_id": "USR-101", "libro_id": "LIB-001"}, "id": "1"}
    modelo = ModeloFalso(messages=iter([AIMessage(content="", tool_calls=[llamada]), AIMessage(content="Cancelado.")]))
    agente = crear_agente(modelo=modelo)
    config = {"configurable": {"thread_id": "t"}}
    antes = copy.deepcopy(servicio.datos)

    agente.invoke({"messages": [("user", "Presta LIB-001 a USR-101")]}, config)
    agente.invoke(Command(resume={"decisions": [{"type": "reject", "message": "No aprobado."}]}), config)

    assert servicio.datos == antes
