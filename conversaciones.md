# Conversaciones de evidencia

Conversaciones **reales** con el agente (`agente.py`) usando Groq, modelo `openai/gpt-oss-120b`, ejecutadas el 2026-11-24. Un script envió los mensajes del usuario y las decisiones del bibliotecario (`s`/`n`) al mismo agente que usa `python agente.py`. Las respuestas del LLM y de las herramientas se copiaron **sin editar**. Antes de cada conversación se recargó `datos.json`, igual que reiniciar el programa.

Las líneas entre corchetes son trazas del sistema: `[LLM invoca herramienta]` es la llamada que propone el modelo, `[APROBACIÓN]` es la pausa del Human-In-The-Loop y `[Resultado de ...]` es lo que devuelve la herramienta.

---

## Conversación 1: Préstamo exitoso con aprobación humana

**Objetivo:** Consulta de catálogo (sin aprobación) y préstamo de escritura (con aprobación).

```text
Usuario: ¿Tienen el libro Cien Años de Soledad?
[LLM invoca herramienta] buscar_libro({'query': 'Cien Años de Soledad'})
[Resultado de buscar_libro] [{'id': 'LIB-001', 'titulo': 'Cien Años de Soledad', 'autor': 'Gabriel García Márquez', 'ejemplares_totales': 3, 'copias_disponibles': 1}]

Asistente: ¡Sí! Tenemos **Cien Años de Soledad** de Gabriel García Márquez en nuestro catálogo. Actualmente hay **1 copia disponible**. 
    
    ¿Te gustaría reservarla o solicitar el préstamo? Si deseas hacerlo, solo necesito tu **identificador de usuario**.

Usuario: Sí, préstalo al usuario USR-101 por favor.
[LLM invoca herramienta] registrar_prestamo({'libro_id': 'LIB-001', 'usuario_id': 'USR-101'})
[APROBACIÓN] ¿Ejecutar registrar_prestamo({'libro_id': 'LIB-001', 'usuario_id': 'USR-101'})? [s/n]: s
[Resultado de registrar_prestamo] Éxito: Préstamo registrado correctamente -> {'id': 'PRE-002', 'usuario_id': 'USR-101', 'libro_id': 'LIB-001', 'fecha_prestamo': '2025-11-20', 'fecha_vencimiento': '2025-11-27', 'renovaciones': 0, 'estado': 'activo'}

Asistente: ¡Listo! El préstamo se ha registrado con éxito.
    
    **Detalles del préstamo**
    - **ID del préstamo:** PRE-002  
    - **Usuario:** USR-101  
    - **Libro:** Cien Años de Soledad (LIB-001)  
    - **Fecha de préstamo:** 20 nov 2025  
    - **Fecha de vencimiento:** 27 nov 2025  
    
    Recuerda devolver el libro antes de la fecha de vencimiento o solicitar una renovación si lo necesitas. ¡Disfruta de la lectura!
```

**Qué demuestra:** `buscar_libro` es de lectura y se ejecuta directo. `registrar_prestamo` pausa el grafo hasta que el bibliotecario responde `s`. El dominio crea `PRE-002` con vencimiento `fecha_hoy + 7` = `2025-11-27` y descuenta la única copia disponible.

---

## Conversación 2: Rechazo por regla de negocio (multa pendiente)

**Objetivo:** Defensa en profundidad: aunque el humano aprueba, el dominio bloquea.

```text
Usuario: Hola, soy el usuario USR-102 y quiero llevarme el libro LIB-001.
[LLM invoca herramienta] registrar_prestamo({'libro_id': 'LIB-001', 'usuario_id': 'USR-102'})
[APROBACIÓN] ¿Ejecutar registrar_prestamo({'libro_id': 'LIB-001', 'usuario_id': 'USR-102'})? [s/n]: s
[Resultado de registrar_prestamo] RECHAZADO POR DOMINIO: El usuario Carlos López tiene una multa pendiente de $50.0.

Asistente: ¡Hola! No he podido registrar el préstamo porque el usuario **USR‑102** (Carlos López) tiene una multa pendiente de **$50.00**. Mientras esa multa no se pague, el sistema no permite hacer nuevos préstamos.
    
    Para poder llevarte el libro, puedes:
    
    1. **Pagar la multa** en la ventanilla de la biblioteca o a través del portal de usuarios.
    2. Una vez que la multa esté saldada, avísame y volveré a intentar registrar el préstamo.
    
    Si necesitas ayuda para saber cómo pagar la multa o tienes alguna otra consulta, ¡dímelo!
```

**Qué demuestra:** El bibliotecario aprueba (`s`), pero `dominio.py` lanza `ErrorDeNegocio` por la multa de $50.00. La herramienta lo convierte en `RECHAZADO POR DOMINIO` y el LLM explica la razón exacta. Ni el LLM ni el humano pueden saltarse una regla de negocio.

---

## Conversación 3: Renovación aprobada y segunda renovación rechazada por el dominio

**Objetivo:** Regla de máximo 1 renovación.

```text
Usuario: Soy USR-101, quiero renovar mi préstamo PRE-001.
[LLM invoca herramienta] renovar_prestamo({'prestamo_id': 'PRE-001'})
[APROBACIÓN] ¿Ejecutar renovar_prestamo({'prestamo_id': 'PRE-001'})? [s/n]: s
[Resultado de renovar_prestamo] Éxito: Préstamo renovado correctamente -> {'id': 'PRE-001', 'usuario_id': 'USR-101', 'libro_id': 'LIB-001', 'fecha_prestamo': '2025-11-15', 'fecha_vencimiento': '2025-11-29', 'renovaciones': 1, 'estado': 'activo'}

Asistente: ¡Listo! Tu préstamo **PRE‑001** ha sido renovado exitosamente. La nueva fecha de vencimiento es el **29 de noviembre de 2025**. Si necesitas algo más, estoy aquí para ayudarte.

Usuario: Perfecto, ¿me lo puedes renovar otra vez?
[LLM invoca herramienta] renovar_prestamo({'prestamo_id': 'PRE-001'})
[APROBACIÓN] ¿Ejecutar renovar_prestamo({'prestamo_id': 'PRE-001'})? [s/n]: s
[Resultado de renovar_prestamo] RECHAZADO POR DOMINIO: El préstamo ya alcanzó el número máximo de renovaciones (1).

Asistente: No se pudo renovar de nuevo porque ese préstamo ya ha alcanzado el número máximo de renovaciones permitidas (solo se permite una renovación).  
    
    Si necesitas devolver el libro, buscar otro título o cualquier otra ayuda relacionada con la biblioteca, avísame y con gusto te ayudo.
```

**Qué demuestra:** La primera renovación extiende `2025-11-22` a `2025-11-29` (`renovaciones = 1`). La segunda, aun aprobada por el humano, la rechaza el dominio. El agente recuerda el préstamo gracias al checkpointer (mismo `thread_id`).

---

## Conversación 4: El bibliotecario rechaza la escritura y pregunta fuera de dominio

**Objetivo:** Rechazo humano (HITL), consulta posterior y pregunta fuera de dominio.

```text
Usuario: Quiero devolver el préstamo PRE-001.
[LLM invoca herramienta] procesar_devolucion({'prestamo_id': 'PRE-001'})
[APROBACIÓN] ¿Ejecutar procesar_devolucion({'prestamo_id': 'PRE-001'})? [s/n]: n
[Resultado de procesar_devolucion] User rejected the tool call for `procesar_devolucion` with reason: El bibliotecario NO aprobó esta operación y no se ejecutó. No es un error del sistema ni de los datos. Informa al usuario que su solicitud no fue autorizada y que acuda al mostrador si tiene dudas.

Asistente: Lo siento, pero la devolución del préstamo **PRE‑001** no ha sido autorizada. Para completar la operación, por favor acércate al mostrador de la biblioteca o contacta a un bibliotecario. Si tienes alguna otra consulta sobre tu cuenta o el catálogo, estaré encantado de ayudarte.

Usuario: Entonces, ¿qué préstamos tengo? Soy USR-101.
[LLM invoca herramienta] consultar_prestamos({'usuario_id': 'USR-101'})
[Resultado de consultar_prestamos] [{'id': 'PRE-001', 'usuario_id': 'USR-101', 'libro_id': 'LIB-001', 'fecha_prestamo': '2025-11-15', 'fecha_vencimiento': '2025-11-22', 'renovaciones': 0, 'estado': 'activo'}]

Asistente: Aquí tienes el detalle de tus préstamos activos:
    
    | Préstamo | Libro | Fecha de préstamo | Fecha de vencimiento | Renovaciones | Estado |
    |----------|-------|-------------------|----------------------|--------------|--------|
    | **PRE-001** | LIB-001 | 15 nov 2025 | 22 nov 2025 | 0 | activo |
    
    Si deseas renovar este préstamo o tienes alguna otra consulta, avísame y con gusto te ayudo.

Usuario: Oye, ¿quién ganó el mundial de fútbol de 2022?

Asistente: Lo siento, pero solo puedo ayudar con temas relacionados con la biblioteca, como el catálogo, préstamos, renovaciones y devoluciones. Si tienes alguna pregunta sobre esos asuntos, estaré encantado de asistirte.
```

**Qué demuestra:** Con `n` la herramienta **no se ejecuta**: la consulta siguiente confirma que `PRE-001` sigue `activo` con su vencimiento original. La pregunta sobre fútbol se rechaza sin invocar herramientas.
