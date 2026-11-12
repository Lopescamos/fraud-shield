# ADR-006: Outbox pattern + idempotencia por `message_id`

- Estado: Aceptada
- Fecha: 2026-11-10

## Contexto

Un servicio que guarda un aggregate y publica un evento habla con **dos sistemas** (base de datos y broker). Si el servicio cae entre los dos pasos, se pierde el evento o se publica algo que nunca se guardó. Además, los brokers entregan **al menos una vez**: cualquier consumidor puede recibir un mensaje duplicado.

## Decisión

### Publicación: Outbox pattern

- En la **misma transacción** que persiste el aggregate, se escribe una fila en `outbox_events` con el evento a publicar.
- Un `OutboxRelayJob` (`@Scheduled`/`APScheduler`) lee filas `PENDING` con `FOR UPDATE SKIP LOCKED`, las publica en Kafka y las marca como `PUBLISHED`.
- Si el relay cae entre publicar y marcar, la fila vuelve a tomarse y se republica. Por eso el consumidor debe ser idempotente.

### Consumo: idempotencia por `message_id`

- Cada consumidor usa `IdempotentExecutor`, que guarda `(message_id, consumer_group)` en `processed_events` en la **misma transacción** que el cambio de negocio.
- Si el `message_id` ya existe para ese grupo, el mensaje se descarta sin ejecutar el command.
- Además, los commands se diseñan **naturalmente idempotentes** cuando es posible (evaluar dos veces la misma `transaction_id` produce un solo `risk_assessment`, respaldado por `UNIQUE (transaction_id)`).

### Reintentos y DLQ

- El consumidor reintenta tres veces con backoff exponencial (1s, 2s, 4s).
- Si agota los reintentos, el mensaje se publica en el tópico `.dlq` correspondiente con los metadatos del error.
- Los errores no recuperables (payload inválido) no se reintentan y van directo a DLQ.

## Alternativas consideradas

- **Publicar al broker directamente desde el command**. Se descarta por el riesgo de perder eventos en caídas entre el `COMMIT` y la publicación.
- **Change Data Capture (Debezium)** sobre la tabla del aggregate. Potente, pero añade un componente operativo que no pagamos en un portafolio.
- **Transacciones distribuidas (XA)**. No soportadas por Kafka y disparan complejidad.

## Consecuencias

- Toda publicación pasa por el Outbox; no hay "escape" directo al broker desde los commands.
- Cada consumidor tiene una tabla `processed_events` en su esquema.
- El sistema es resiliente a caídas intermedias y a duplicados, al costo de una tabla extra por servicio y un job de relay.
