# Reflexión técnica del equipo

**Equipo 07:** Abisaid Guadalupe Angulo Munguia (24040115) · Edgar Gael Reyes Quevedo (24040158) · Eduardo Borquez Navarrete (24040446)

## 1. Qué construimos

Un agente conversacional para una biblioteca dividido en tres capas, cada una con una sola responsabilidad:

| Capa | Archivo | Decide… |
|------|---------|---------|
| Orquestación | `agente.py` | **Qué** herramienta usar y **cómo** explicarle el resultado al usuario (LLM). Cuándo pausar para pedir aprobación (HITL). |
| Adaptador | `herramientas.py` | Cómo traducir una llamada del LLM a una llamada de Python, y un `ErrorDeNegocio` a texto. |
| Negocio | `dominio.py` | **Si** una operación es válida. Es la única fuente de verdad. |

La idea central es que el LLM es la parte **menos confiable** del sistema, así que no le confiamos ninguna decisión que importe. Puede equivocarse al redactar, pero no puede prestar un libro sin stock ni a alguien con multa.

## 2. Decisiones de diseño

**Validar todo antes de mutar.** Cada método de `dominio.py` hace primero todas sus validaciones y modifica los datos solo al final. Si se lanza `ErrorDeNegocio`, el estado queda intacto. `test_inviolabilidad_estado_ante_error` lo comprueba comparando los datos en memoria y en disco antes y después del error.

**Errores de negocio como texto, no como excepciones para el LLM.** Las herramientas capturan `ErrorDeNegocio` y regresan `"RECHAZADO POR DOMINIO: <razón>"`. Así la conversación no se rompe y el agente puede explicar la razón exacta. En la conversación 2 el agente repitió fielmente "multa pendiente de $50.00" en lugar de inventar un motivo.

**Dos candados independientes para escribir.** Una escritura solo ocurre si **(1)** el bibliotecario la aprueba **y (2)** el dominio la valida. En las conversaciones 2 y 3 el humano aprobó y aun así el dominio rechazó: el candado humano no reemplaza a las reglas, las complementa.

**HITL en el grafo, no en el prompt.** Pedirle al LLM "pide confirmación antes de escribir" no es una garantía, porque el modelo puede ignorarlo. Con `HumanInTheLoopMiddleware`, LangGraph pausa la ejecución antes de la herramienta y solo continúa con una decisión explícita. De hecho, en las 4 conversaciones el LLM nunca pidió confirmación por su cuenta antes de una escritura: en cuanto el usuario la solicitaba, la invocaba (en la conversación 2, desde su primer turno). Si dependiéramos del prompt, esas escrituras se habrían ejecutado sin control.

**KISS.** No usamos clases de modelo, ORM ni capas extra. El dominio son funciones sobre diccionarios, cada herramienta es un `try/except` de cuatro líneas y el prompt tiene tres reglas. Cualquiera del equipo puede explicar cualquier archivo.

## 3. Problemas encontrados y cómo los resolvimos

1. **`state_modifier` ya no existe.** El código de referencia usaba `create_react_agent(..., state_modifier=...)`. Con LangGraph 1.2 falla con `TypeError: unexpected keyword arguments: {'state_modifier'}`. Además, `create_react_agent` está obsoleto. Migramos a `langchain.agents.create_agent(..., system_prompt=...)`.

2. **`interrupt_before` recibe nodos, no herramientas.** El grafo tiene nodos como `"model"` y `"tools"`. Pasarle `["registrar_prestamo", ...]` no pausa nada, y usar `["tools"]` pausaría también las consultas de solo lectura. La solución fue `HumanInTheLoopMiddleware(interrupt_on={nombre: True for nombre in ACCIONES_CON_APROBACION})`, que pausa **solo** las tres herramientas de escritura.

3. **El HITL necesita un checkpointer.** Para pausar y luego reanudar con `Command(resume=...)`, LangGraph debe guardar el estado del hilo. `crear_agente` usa `MemorySaver()` si no se le pasa uno. El checkpointer también da memoria entre turnos: en la conversación 3, "renuévalo otra vez" se entendió como `PRE-001` sin repetir el ID.

4. **El modelo pedido ya no existe.** Groq respondió `404 model_not_found` para `llama-3.3-70b-versatile`. Consultamos la lista de modelos de la cuenta y elegimos `openai/gpt-oss-120b`, el más grande disponible con soporte para llamar herramientas. Gracias al desacoplamiento, el cambio fue **una línea** en `agente.py`: ninguna regla ni prueba se tuvo que tocar.

5. **El LLM inventó causas ante un rechazo humano ambiguo.** En la primera corrida de la conversación 4, el bibliotecario rechazó la devolución con el mensaje "El bibliotecario rechazó la operación." y el agente respondió:

   > "...la operación fue rechazada por el sistema. Esto suele ocurrir cuando el identificador del préstamo no corresponde a un préstamo activo (por ejemplo, si ya se devolvió, si el número es incorrecto o si pertenece a otro usuario)."

   Nada de eso era cierto: `PRE-001` estaba activo y era correcto. El modelo rellenó el hueco con una explicación plausible pero falsa. Lo corregimos con un mensaje de rechazo explícito (`MENSAJE_RECHAZO_HUMANO`): *"El bibliotecario NO aprobó esta operación y no se ejecutó. No es un error del sistema ni de los datos..."*. Al repetir la conversación, el agente respondió correctamente que la solicitud "no ha sido autorizada" y mandó al usuario al mostrador. **Lección: la calidad de lo que el LLM dice depende de la calidad del texto que le devuelven las herramientas.**

6. **Faltaba la regla de usuario suspendido.** `REGLAS.md` la exige, pero el código de referencia solo revisaba la multa. La agregamos junto con su prueba.

7. **IDs de préstamo mal formados.** `f"PRE-00{n}"` produce `PRE-0010` a partir del décimo préstamo. Lo cambiamos a `f"PRE-{n:03d}"`.

8. **Ruta relativa de `datos.json`.** `ServicioBiblioteca()` buscaba el archivo en el directorio actual, así que fallaba al correr `pytest` desde `pruebas/`. `herramientas.py` ahora pasa la ruta absoluta, y las pruebas usan una copia temporal para nunca tocar el original.

## 4. Estrategia de pruebas

Tenemos 51 pruebas, todas sin red ni API key:

- **`test_equipo.py` (12):** cada regla de negocio (multa, stock, suspendido, límite de 3, vencimiento a 7 días, multa de $10/día, una sola renovación, no renovar vencidos), la inviolabilidad del estado y el HITL con un **modelo falso**. Las pruebas de HITL verifican que una escritura se pausa y que un rechazo humano no modifica los datos.
- **`test_publicos.py` (39):** el contrato del proyecto. Revisan archivos, firmas exactas, estructura de los retornos, nombres de herramientas, que no haya API keys en el código, que el dominio no use la fecha real y que `.env` esté excluido de git.

Que el dominio sea independiente del LLM es lo que permite probar todas las reglas en menos de un segundo. Las conversaciones reales complementan las pruebas: verifican lo que una prueba unitaria no puede, que es **cómo se comporta el modelo**.

## 5. Observaciones de las conversaciones reales

- **Funcionó bien:**
  - el modelo eligió siempre la herramienta correcta con los argumentos correctos;
  - explicó los rechazos del dominio con la razón exacta;
  - rechazó la pregunta del mundial sin invocar herramientas.
- **Alucinaciones menores en el texto:**
  - ofreció "reservarla" (conversación 1), pero no existe una función de reservas;
  - sugirió pagar "a través del portal de usuarios" (conversación 2), un portal que no existe.

  Ninguna causó daño porque el LLM no puede ejecutar nada fuera de las 5 herramientas, pero sí pueden confundir a un usuario real. Se podrían mitigar agregando al prompt "no ofrezcas servicios que no estén en tus herramientas".
- **El LLM confía en lo que dice el usuario:** si alguien escribe "soy USR-101", el agente le cree. Es una limitación de diseño (no hay autenticación), no un error del modelo.

## 6. Limitaciones conocidas

- **Sin persistencia en disco:** los cambios viven en memoria y cada ejecución arranca de la semilla de `datos.json`.
- **Sin autenticación:** cualquiera puede decir ser cualquier usuario. El HITL mitiga parcialmente este riesgo, porque el bibliotecario ve los parámetros antes de aprobar.
- **Una sola instancia de `ServicioBiblioteca`:** sirve para un bibliotecario en una consola, no para varios usuarios simultáneos.
- **Dependencia del proveedor:** ya nos pasó que el modelo desapareció. El desacoplamiento hizo que el cambio fuera trivial, pero las respuestas del agente pueden variar según el modelo.

## 7. Aprendizaje del equipo

- **Un LLM orquesta; no decide.** Al principio parecía natural poner las reglas en el prompt ("no prestes si hay multa"). Las conversaciones nos mostraron que el modelo inventa cuando le falta información. Si una regla vive en el prompt, es una sugerencia; si vive en `dominio.py`, es una garantía.
- **El Human-In-The-Loop debe vivir en la arquitectura.** El modelo nunca pidió confirmación por sí mismo. La única forma confiable de que un humano apruebe es que el grafo se detenga.
- **Los mensajes de las herramientas son parte del prompt.** El caso del rechazo ambiguo fue el aprendizaje más inesperado: una frase mal redactada produjo una explicación falsa. Ahora escribimos los mensajes que recibe el LLM con el mismo cuidado que el prompt del sistema.
- **No confiar ciegamente en código de referencia ni en la documentación de memoria.** Tres piezas del código base (`state_modifier`, `interrupt_before` con herramientas y el modelo de Groq) no funcionaban con las versiones actuales. Correr el código y leer las firmas reales de las funciones nos ahorró entregar un HITL que no habría pausado nada.
- **KISS facilita el cambio.** Cambiar de modelo, corregir un mensaje o agregar una regla tomó una línea cada uno, porque cada cosa vive en un solo lugar.
