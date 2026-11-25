# Reglas de Negocio — Biblioteca

Todas las reglas se validan **exclusivamente** en `dominio.py`. Cualquier violación lanza `ErrorDeNegocio` y **no modifica** el estado. El LLM nunca decide si una regla se cumple: solo orquesta la conversación.

## Fecha del sistema

- Se opera **únicamente** con `fecha_hoy` de `datos.json` (actualmente `2025-11-20`).
- Está prohibido usar `datetime.date.today()`.

## Préstamos (`registrar_prestamo`)

| # | Regla | Mensaje de rechazo |
|---|-------|--------------------|
| P1 | El usuario debe existir. | `El usuario '<id>' no existe.` |
| P2 | Un usuario con `estado == "suspendido"` no puede pedir préstamos. | `El usuario <nombre> está suspendido.` |
| P3 | Un usuario con `multa_pendiente > 0` no puede pedir préstamos. | `El usuario <nombre> tiene una multa pendiente de $<monto>.` |
| P4 | Máximo **3 préstamos activos** simultáneos por usuario. | `El usuario ha alcanzado el límite máximo de 3 préstamos activos.` |
| P5 | El libro debe existir. | `El libro '<id>' no existe.` |
| P6 | No se presta si `copias_disponibles <= 0`. | `El libro '<titulo>' no tiene copias disponibles.` |
| P7 | Vencimiento por defecto: `fecha_hoy + 7` días naturales. | — |

Efecto si todo es válido: `copias_disponibles -= 1` y se agrega un préstamo `"activo"` con `renovaciones = 0`.

## Devoluciones (`procesar_devolucion`)

| # | Regla |
|---|-------|
| D1 | Solo se devuelve un préstamo existente en estado `"activo"`. |
| D2 | Al devolver: `copias_disponibles += 1` y el préstamo pasa a `"devuelto"`. |
| D3 | Si `fecha_hoy > fecha_vencimiento`, multa de **$10.00 MXN por día de retraso**, que se suma a `multa_pendiente` del usuario. |

## Renovaciones (`renovar_prestamo`)

| # | Regla |
|---|-------|
| R1 | Solo se renueva un préstamo en estado `"activo"`. |
| R2 | No se renueva un préstamo vencido (`fecha_hoy > fecha_vencimiento`). |
| R3 | Máximo **1 renovación** por préstamo; extiende `fecha_vencimiento` 7 días. |

## Aprobación humana (HITL)

Las herramientas de escritura `registrar_prestamo`, `procesar_devolucion` y `renovar_prestamo` se pausan antes de ejecutarse y solo corren si el bibliotecario las aprueba. Las consultas (`buscar_libro`, `consultar_prestamos`) no requieren aprobación.

## Persistencia

`datos.json` es la semilla del sistema. Los cambios viven en memoria durante la sesión y **no** se escriben en disco; cada ejecución arranca del mismo estado inicial.
