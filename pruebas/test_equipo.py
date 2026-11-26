import copy
import json

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from langgraph.types import Command

from dominio import ErrorDeNegocio
from herramientas import Contexto
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


PRESTAR = {"name": "registrar_prestamo", "args": {"usuario_id": "USR-101", "libro_id": "LIB-001"}, "id": "1"}
CONFIG = {"configurable": {"thread_id": "t"}}


def agente_falso(*respuestas):
    return crear_agente(ModeloFalso(messages=iter(respuestas)))


def test_escritura_se_pausa_hasta_aprobacion(servicio):
    agente = agente_falso(AIMessage(content="", tool_calls=[PRESTAR]))

    resultado = agente.invoke({"messages": [("user", "Presta LIB-001 a USR-101")]}, CONFIG, context=Contexto(servicio))

    assert resultado["__interrupt__"][0].value["action_requests"][0]["name"] == "registrar_prestamo"
    assert len(servicio.datos["prestamos"]) == 1  # Pausado: todavía no se escribió nada.


def test_escritura_aprobada_se_ejecuta(servicio):
    agente = agente_falso(AIMessage(content="", tool_calls=[PRESTAR]), AIMessage(content="Listo."))
    contexto = Contexto(servicio)

    agente.invoke({"messages": [("user", "Presta LIB-001 a USR-101")]}, CONFIG, context=contexto)
    agente.invoke(Command(resume={"decisions": [{"type": "approve"}]}), CONFIG, context=contexto)

    assert servicio.datos["prestamos"][-1]["id"] == "PRE-002"


def test_escritura_rechazada_no_modifica_datos(servicio):
    agente = agente_falso(AIMessage(content="", tool_calls=[PRESTAR]), AIMessage(content="Cancelado."))
    contexto = Contexto(servicio)
    antes = copy.deepcopy(servicio.datos)

    agente.invoke({"messages": [("user", "Presta LIB-001 a USR-101")]}, CONFIG, context=contexto)
    agente.invoke(Command(resume={"decisions": [{"type": "reject", "message": "No aprobado."}]}), CONFIG, context=contexto)

    assert servicio.datos == antes


def test_lectura_no_pide_aprobacion(servicio):
    buscar = {"name": "buscar_libro", "args": {"query": "cien"}, "id": "1"}
    agente = agente_falso(AIMessage(content="", tool_calls=[buscar]), AIMessage(content="Sí lo tenemos."))

    resultado = agente.invoke({"messages": [("user", "¿Tienen Cien Años?")]}, CONFIG, context=Contexto(servicio))

    assert "__interrupt__" not in resultado
    assert "Cien Años de Soledad" in resultado["messages"][-2].content


def test_memoria_por_thread_id(servicio):
    agente = agente_falso(AIMessage(content="Hola Ana."), AIMessage(content="Te llamas Ana."))
    contexto = Contexto(servicio)

    agente.invoke({"messages": [("user", "Me llamo Ana")]}, CONFIG, context=contexto)
    resultado = agente.invoke({"messages": [("user", "¿Cómo me llamo?")]}, CONFIG, context=contexto)

    assert [m.content for m in resultado["messages"]][0] == "Me llamo Ana"  # El hilo recuerda el mensaje anterior.
    otro_hilo = agente.get_state({"configurable": {"thread_id": "otro"}}).values
    assert not otro_hilo  # Otro thread_id empieza sin historial.
