import json
from datetime import datetime, timedelta
from pathlib import Path

RUTA_DATOS = Path(__file__).parent / "datos.json"


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
        # La fecha del sistema sale SIEMPRE de datos.json, nunca del reloj de la computadora.
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
        # 1) Validaciones: todas antes de tocar los datos.
        usuario = next((u for u in self.datos["usuarios"] if u["id"] == usuario_id), None)
        if not usuario:
            raise ErrorDeNegocio(f"El usuario '{usuario_id}' no existe.")
        if usuario["estado"] == "suspendido":
            raise ErrorDeNegocio(f"El usuario {usuario['nombre']} está suspendido.")
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

        # 2) Mutación simple.
        libro["copias_disponibles"] -= 1
        fecha_vencimiento = self.hoy + timedelta(days=7)
        nuevo_prestamo = {
            "id": f"PRE-{len(self.datos['prestamos']) + 1:03d}",
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


def cargar_servicio(ruta=None) -> ServicioBiblioteca:
    """Crea el servicio con los datos de `ruta` (por defecto, el datos.json del proyecto)."""
    return ServicioBiblioteca(ruta or RUTA_DATOS)
