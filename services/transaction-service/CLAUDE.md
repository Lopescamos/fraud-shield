# transaction-service — CLAUDE.md

## 1. Rol en el sistema
Bounded context de **Transacciones**. Recibe transacciones por API, las persiste con idempotencia (`Idempotency-Key`) y publica `TransactionReceivedV1` por el patrón Outbox.

## 2. Lenguaje ubicuo
- **Transaction**: aggregate con `id` UUID generado por el dominio.
- **AccountId**: VO con identificador plano; `hashed()` devuelve SHA-256 (irreversible) para publicación.
- **Money**: VO `(amount, currency)` con `amount > 0` y `currency` ISO-4217.
- **Channel**: enum `WEB | MOBILE | POS`.
- **Outbox**: tabla `tx.outbox_events` escrita en la misma transacción que la persistencia del aggregate.
- **Idempotency key**: cabecera HTTP `Idempotency-Key`; se guarda en `tx.idempotency_keys`.

## 3. Agregados
- `Transaction` — inmutable una vez registrada. Expone `register(command)` (crea `id`, emite `TransactionRegisteredEvent`) y `restore(...)` (reconstrucción sin eventos).

## 4. Mensajes
### Consume
- (ninguno al inicio)
### Publica
- `TransactionReceivedV1` en `transactions.received.v1` (key: `account_id_hash`).

## 5. Endpoints
- `POST /api/v1/transactions` — registrar una transacción (202). Soporta `Idempotency-Key`.
- `GET /api/v1/transactions/{id}` — devolver la transacción.
- `GET /health`, `GET /ready` — probes.

## 6. Reglas específicas
- `TRANSACTION_OUTBOX_RELAY_ENABLED` arranca en `false`: el relay a Kafka se enciende cuando Kafka esté disponible.
- El `message_id` del Outbox es la base de la idempotencia del consumidor.
- El `account_id` se guarda **solo como hash** en todas las tablas y eventos que salen del servicio.

## 7. Referencias
- Historias: US-01, US-03, US-04 (ver `docs/user-stories_1.md`).
- ADRs: ADR-005 (id por dominio), ADR-006 (Outbox + idempotencia), ADR-004 (postgres por servicio).
