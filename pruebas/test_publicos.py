"""Pruebas públicas: verifican el CONTRATO del proyecto (archivos, firmas, retornos y reglas de oro)."""
import inspect
import json
import re
from pathlib import Path

import pytest

from conftest import RAIZ
from dominio import ErrorDeNegocio, ServicioBiblioteca
import herramientas
import agente

ARCHIVOS_PY = ["dominio.py", "herramientas.py", "agente.py"]


# ---------- Estructura del proyecto ----------

@pytest.mark.parametrize("archivo", [
    "README.md", "reflexion.md", "conversaciones.md", "REGLAS.md", "datos.json",
    "dominio.py", "herramientas.py", "agente.py",
    "pruebas/conftest.py", "pruebas/test_publicos.py", "pruebas/test_equipo.py",
])
def test_estructura_de_archivos(archivo):
    assert (RAIZ / archivo).is_file()


def test_semilla_datos_json():
    datos = json.loads((RAIZ / "datos.json").read_text(encoding="utf-8"))
    assert datos["fecha_hoy"] == "2025-11-20"
    assert {"libros", "usuarios", "prestamos"} <= datos.keys()


# ---------- Contrato de dominio.py ----------

def test_error_de_negocio_es_excepcion():
    assert issubclass(ErrorDeNegocio, Exception)


@pytest.mark.parametrize("metodo, parametros", [
    ("buscar_libro", ["titulo_o_autor"]),
    ("obtener_prestamos_usuario", ["usuario_id"]),
    ("registrar_prestamo", ["usuario_id", "libro_id"]),
    ("procesar_devolucion", ["prestamo_id"]),
    ("renovar_prestamo", ["prestamo_id"]),
])
def test_firmas_del_dominio(metodo, parametros):
    firma = inspect.signature(getattr(ServicioBiblioteca, metodo))
    assert list(firma.parameters)[1:] == parametros


def test_fecha_sale_de_datos_json(servicio):
    assert servicio.hoy.isoformat() == "2025-11-20"


def test_retorno_buscar_libro(servicio):
    resultado = servicio.buscar_libro("márquez")
    assert isinstance(resultado, list) and resultado[0]["id"] == "LIB-001"


def test_retorno_registrar_prestamo(servicio):
    prestamo = servicio.registrar_prestamo("USR-101", "LIB-001")
    assert set(prestamo) == {"id", "usuario_id", "libro_id", "fecha_prestamo", "fecha_vencimiento", "renovaciones", "estado"}
    assert prestamo["estado"] == "activo"


def test_retorno_procesar_devolucion(servicio):
    assert servicio.procesar_devolucion("PRE-001") == {"prestamo_id": "PRE-001", "multa_generada": 0.0, "estado": "devuelto"}


def test_retorno_renovar_prestamo(servicio):
    prestamo = servicio.renovar_prestamo("PRE-001")
    assert prestamo["renovaciones"] == 1 and prestamo["fecha_vencimiento"] == "2025-11-29"


# ---------- Contrato de herramientas.py ----------

def test_nombres_de_herramientas():
    assert [h.name for h in herramientas.HERRAMIENTAS] == [
        "buscar_libro", "consultar_prestamos", "registrar_prestamo", "procesar_devolucion", "renovar_prestamo"
    ]


def test_herramientas_tienen_descripcion():
    assert all(h.description for h in herramientas.HERRAMIENTAS)


def test_herramientas_de_lectura_retornan_texto():
    assert "Cien Años de Soledad" in herramientas.buscar_libro.invoke({"query": "cien"})
    assert "PRE-001" in herramientas.consultar_prestamos.invoke({"usuario_id": "USR-101"})


@pytest.mark.parametrize("herramienta, args", [
    ("registrar_prestamo", {"usuario_id": "USR-102", "libro_id": "LIB-001"}),
    ("procesar_devolucion", {"prestamo_id": "PRE-999"}),
    ("renovar_prestamo", {"prestamo_id": "PRE-999"}),
])
def test_herramientas_capturan_error_de_negocio(herramienta, args):
    respuesta = getattr(herramientas, herramienta).invoke(args)
    assert respuesta.startswith("RECHAZADO POR DOMINIO:")


# ---------- Contrato de agente.py ----------

def test_firma_crear_agente():
    firma = inspect.signature(agente.crear_agente)
    assert list(firma.parameters) == ["modelo", "checkpointer"]
    assert all(p.default is None for p in firma.parameters.values())


def test_acciones_con_aprobacion_son_herramientas_reales():
    nombres = {h.name for h in herramientas.HERRAMIENTAS}
    assert set(agente.ACCIONES_CON_APROBACION) <= nombres
    assert "buscar_libro" not in agente.ACCIONES_CON_APROBACION
    assert "consultar_prestamos" not in agente.ACCIONES_CON_APROBACION


def test_sin_api_key_lanza_error(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        agente.crear_agente()


def test_prompt_sistema_menciona_rechazo_de_dominio():
    assert "RECHAZADO POR DOMINIO" in agente.PROMPT_SISTEMA


# ---------- Reglas de oro ----------

@pytest.mark.parametrize("archivo", ARCHIVOS_PY)
def test_cero_api_keys_en_codigo(archivo):
    codigo = (RAIZ / archivo).read_text(encoding="utf-8")
    assert not re.search(r"gsk_[A-Za-z0-9]{10,}", codigo)


def test_api_key_se_lee_con_getenv():
    assert 'os.getenv("GROQ_API_KEY")' in (RAIZ / "agente.py").read_text(encoding="utf-8")


def test_dominio_no_usa_fecha_real():
    codigo = (RAIZ / "dominio.py").read_text(encoding="utf-8")
    assert "today()" not in codigo and "now()" not in codigo


def test_env_excluido_de_git():
    assert ".env" in (RAIZ / ".gitignore").read_text(encoding="utf-8").split()
