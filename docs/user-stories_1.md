# User stories por épica

Cada historia sigue el formato: **Como** `<rol>`, **quiero** `<acción>`, **para** `<beneficio>`, con criterios de aceptación en `Dado-Cuando-Entonces`.

## E1 — Ingesta y publicación de transacciones

### US-01 — Registrar una transacción individual
Como sistema de ingesta, quiero enviar una transacción por API para que sea evaluada por el motor de riesgo.

- Dado un payload válido, cuando envío `POST /api/v1/transactions`, entonces el sistema responde `202 Accepted` con el `transaction_id` y el evento `TransactionReceivedV1` queda en el Outbox.
- Dado un payload inválido, cuando envío la petición, entonces el sistema responde `422` con la lista de campos fallidos.
- Dado un `account_id` desconocido, cuando envío la petición, entonces el sistema crea el perfil de la cuenta y continúa.

### US-02 — Enviar un lote de transacciones
Como sistema de ingesta, quiero enviar un lote para reducir llamadas.

- Dado un lote de hasta 500 transacciones, cuando envío `POST /api/v1/transactions/batch`, entonces el sistema responde `202` con el conteo aceptado y publica un evento por transacción.
- Dado un lote con más de 500 ítems, cuando lo envío, entonces el sistema responde `413` sin procesar.

### US-03 — Idempotencia por `Idempotency-Key`
Como sistema de ingesta, quiero reintentar sin duplicar transacciones.

- Dado un reenvío con la misma `Idempotency-Key`, cuando llega al sistema, entonces este devuelve el mismo `transaction_id` sin crear otra transacción ni emitir otro evento.

### US-04 — Consultar una transacción
Como cliente, quiero consultar el estado y el puntaje de una transacción.

- Dado un `transaction_id` existente, cuando llamo `GET /api/v1/transactions/{id}`, entonces el sistema devuelve datos, estado y, si existe, el `RiskAssessment` asociado.

## E2 — Scoring determinístico y explicable

### US-05 — Evaluar una transacción
Como motor de scoring, quiero evaluar cada transacción recibida para producir un puntaje y un nivel.

- Dado un evento `TransactionReceivedV1`, cuando el servicio lo consume, entonces persiste un `RiskAssessment` con `score`, `level`, reglas activadas y factores SHAP.
- Dado que el modelo ML no está disponible, cuando se evalúa una transacción, entonces el sistema usa solo reglas y marca `degraded_mode=true`.

### US-06 — Previsualizar un puntaje sin persistir
Como analista, quiero evaluar una transacción de prueba sin dejarla registrada.

- Dado un payload válido, cuando llamo `POST /api/v1/score/preview`, entonces el sistema devuelve el puntaje y la explicación sin guardar nada.

### US-07 — Explicabilidad SHAP
Como analista, quiero ver qué llevó al modelo a ese puntaje.

- Dado un `RiskAssessment` persistido, cuando lo consulto, entonces incluye los tres factores SHAP con mayor impacto y su valor relativo.

### US-08 — Consultar el modelo activo
Como administrador, quiero saber qué versión de modelo está evaluando.

- Dado el servicio arrancado, cuando llamo `GET /api/v1/models/active`, entonces el sistema devuelve `version`, `trained_at` y métricas de validación (precisión, recall, PR-AUC).

## E3 — Alertas y ciclo de vida

### US-09 — Generar alerta automática
Como motor de alertas, quiero crear una alerta cuando el nivel sea alto o crítico.

- Dado un evento `TransactionScoredV1` con `level ∈ {HIGH, CRITICAL}`, cuando el servicio lo consume, entonces crea una `FraudAlert` en estado `OPEN` y publica `AlertRaisedV1`.

### US-10 — Cambiar el estado de una alerta
Como analista, quiero mover una alerta a lo largo de su ciclo.

- Dado una alerta en `OPEN`, cuando llamo `PATCH /api/v1/alerts/{id}/status` con `IN_REVIEW`, entonces el sistema actualiza el estado y registra el cambio en el historial.
- Dado una alerta en `CONFIRMED` o `DISMISSED`, cuando intento reabrirla sin motivo, entonces el sistema responde `400`.

### US-11 — Agregar notas de investigación
Como analista, quiero adjuntar notas a una alerta.

- Dado una alerta existente, cuando llamo `POST /api/v1/alerts/{id}/notes`, entonces el sistema guarda la nota con `author`, `created_at` y la asocia a la alerta.

### US-12 — Consultar alertas pendientes
Como analista, quiero ver mi bandeja de alertas.

- Dado parámetros `status` y `severity`, cuando llamo `GET /api/v1/alerts`, entonces el sistema devuelve la lista paginada ordenada por antigüedad.

## E4 — Notificaciones por n8n

### US-13 — Enviar alerta a n8n
Como motor de alertas, quiero avisar a n8n cuando ocurre una alerta crítica.

- Dado un evento `AlertRaisedV1` con `level=CRITICAL`, cuando el servicio lo publica, entonces se emite un webhook hacia n8n con el payload definido.
- Dado que n8n no responde, cuando se intenta el webhook, entonces se reintenta hasta tres veces y, si falla, se registra pero no se afecta la alerta.

## E5 — API de analítica para Power BI

### US-14 — Obtener KPIs del periodo
Como analista de negocio, quiero ver KPIs agregados.

- Dado `from` y `to`, cuando llamo `GET /bi/v1/kpis`, entonces el sistema devuelve transacciones, alertas, tasa de alerta, monto en riesgo y tiempo medio de investigación del periodo.

### US-15 — Obtener serie temporal
Como analista, quiero graficar la evolución.

- Dado `from`, `to`, `granularity`, cuando llamo `GET /bi/v1/timeseries`, entonces el sistema devuelve una serie por hora o día de transacciones y alertas.

### US-16 — Autenticar con API key
Como cliente Power BI, quiero autenticarme con una clave de solo lectura.

- Dado el encabezado `X-API-Key` con rol `bi_reader`, cuando llamo un endpoint `/bi/v1`, entonces se autoriza; sin encabezado o con rol equivocado, el sistema responde `401` o `403`.

### US-17 — Rate limiting por clave
Como operador, quiero evitar abusos de la API.

- Dado una API key, cuando supera 60 solicitudes por minuto, entonces el sistema responde `429` con la cabecera `Retry-After`.

## E6 — Gestión de accesos

### US-18 — Iniciar sesión de analista
Como analista, quiero autenticarme en el sistema.

- Dado credenciales válidas, cuando llamo `POST /api/v1/auth/login`, entonces el sistema devuelve un JWT de 15 min y un refresh token.
- Dado credenciales inválidas, cuando llamo el endpoint, entonces el sistema responde `401` sin pistas sobre qué campo falló.

### US-19 — Renovar JWT
Como analista, quiero mantener la sesión sin reingresar credenciales.

- Dado un refresh token válido, cuando llamo `POST /api/v1/auth/refresh`, entonces el sistema devuelve un nuevo JWT.

### US-20 — Crear API keys
Como administrador, quiero emitir claves para sistemas cliente.

- Dado un rol válido, cuando llamo `POST /api/v1/api-keys` con `role` y `description`, entonces el sistema devuelve la clave una sola vez y guarda su hash.

## E7 — Mensajería confiable

### US-21 — Garantizar publicación con Outbox
Como transaction-service, quiero no perder eventos por fallos intermedios.

- Dado que persisto una transacción, cuando ocurre `COMMIT`, entonces hay una fila en `outbox` con el evento, y un relay la publica en Kafka más tarde.
- Dado el relay cae tras publicar y antes de marcar, cuando se reinicia, entonces el mensaje se republica (al menos una vez) y el consumidor lo descarta por idempotencia.

### US-22 — Consumir mensajes idempotentes
Como cualquier consumidor, quiero procesar duplicados sin efecto doble.

- Dado un mensaje con `message_id` ya procesado, cuando llega al consumidor, entonces se descarta sin ejecutar el command.

### US-23 — Enviar mensajes fallidos a DLQ
Como operador, quiero inspeccionar mensajes que fallan siempre.

- Dado un mensaje que falla tres reintentos con backoff, cuando se agota, entonces se publica en el tópico `.dlq` correspondiente con los metadatos del error.

### US-24 — Versionar contratos
Como desarrollador de contratos, quiero cambiar un contrato sin romper consumidores.

- Dado un cambio compatible (campo opcional), cuando el emisor publica V1 con el nuevo campo, entonces los consumidores viejos siguen funcionando.
- Dado un cambio incompatible, cuando quiero emitirlo, entonces creo `V2` y publico ambas versiones hasta migrar.

## E8 — Observabilidad y operación

### US-25 — Probes de salud
Como orquestador, quiero saber si un servicio está vivo y listo.

- Dado el servicio arrancado, cuando llamo `/health`, entonces responde `200` con `{"status":"UP"}`.
- Dado la base de datos o Kafka inalcanzables, cuando llamo `/ready`, entonces responde `503`.

### US-26 — Trazar una transacción de punta a punta
Como desarrollador, quiero seguir una transacción por todos los servicios.

- Dado un `trace_id` emitido por el gateway, cuando una transacción es procesada, entonces el `trace_id` aparece en los logs de cada servicio por el que pasa y en los eventos Kafka relacionados.

### US-27 — Métricas Prometheus
Como operador, quiero medir el sistema.

- Dado cada servicio, cuando llamo `/metrics`, entonces expone contadores de transacciones por segundo, latencia de scoring, lag por consumer group y mensajes en DLQ.

## E9 — CI/CD y empaquetado

### US-28 — Pipeline en cada PR
Como desarrollador, quiero validar cambios antes del merge.

- Dado un pull request, cuando GitHub Actions corre, entonces ejecuta lint (ruff), tipos (mypy), tests unitarios y de integración, y valida contratos; un fallo bloquea el merge.

### US-29 — Publicar imágenes Docker
Como equipo, quiero imágenes versionadas listas para desplegar.

- Dado un merge a `main`, cuando el pipeline completa, entonces construye imágenes de los cinco servicios y las publica en GHCR con la etiqueta del commit.

### US-30 — Puerta de calidad del modelo
Como equipo, quiero bloquear despliegues si el modelo empeora.

- Dado el entrenamiento reproducible en CI, cuando el `recall` del modelo nuevo baja del umbral acordado, entonces el pipeline falla.

## E10 — Dataset y simulador de tráfico

### US-31 — Generar tráfico sintético
Como desarrollador, quiero probar el sistema end-to-end con tráfico variado.

- Dado el `traffic-simulator` ejecutado, cuando corre por 10 minutos, entonces envía al menos 10.000 transacciones a la API con una mezcla configurable de operaciones normales y escenarios de fraude (ráfaga, monto atípico, viaje imposible).

### US-32 — Descargar dataset público
Como desarrollador, quiero entrenar con datos reales de referencia.

- Dado un script `scripts/download_dataset.py`, cuando lo ejecuto, entonces descarga el dataset Credit Card Fraud desde Kaggle (o PaySim) a `data/raw/`, respetando la licencia.
