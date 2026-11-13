# alert-service — CLAUDE.md

## 1. Rol en el sistema
Bounded context de **Alertas**. Consume `TransactionScoredV1`, decide si la transacción merece alerta (según la `decision` que trae el evento), gestiona el ciclo de vida de la `Alert` (OPEN → IN_REVIEW → RESOLVED/DISMISSED) y expone una API REST para el analista.

## 2. Lenguaje ubicuo
- **Alert**: aggregate con `id` UUID generado por el dominio, `status` y `priority` derivada del `risk_score`.
- **AlertStatus**: enum `OPEN | IN_REVIEW | RESOLVED | DISMISSED`.
- **Priority**: enum `LOW | MEDIUM | HIGH | CRITICAL`. `Priority.from_risk_score(score)` aplica los umbrales (`>=90` CRITICAL, `>=75` HIGH, `>=50` MEDIUM, resto LOW).
- **RiskFactor**: VO duplicado aquí para no depender del paquete `scoring`; mismo shape (`feature, weight, direction, source`).
- **Outbox**: tabla `alerts.outbox_events` escrita en la misma transacción que el aggregate.
- **Processed events**: `alerts.processed_events` idempotencia del consumer.

## 3. Agregados
- `Alert` — expone `register(...)` (OPEN + evento `AlertRaised`), `assign(analyst_id)` (OPEN → IN_REVIEW), `resolve(notes)` (IN_REVIEW → RESOLVED + evento `AlertResolved`), `dismiss(reason)` (IN_REVIEW → DISMISSED + evento `AlertResolved` con `new_status=DISMISSED`), `restore(...)` (sin eventos).
- Transiciones inválidas lanzan `InvalidAlertTransition`; la capa application las convierte a `Failure(ApplicationError.business_rule_violation(...))`.

## 4. Mensajes
### Consume
- `TransactionScoredV1` (topic `transactions.scored.v1`, grupo `alert.raise-on-scored`) — consumer presente pero **desactivado** por `ALERT_CONSUMER_ENABLED=false` hasta que Kafka esté arriba.
### Publica
- `AlertRaisedV1` en `alerts.raised.v1` (key: `alert_id`).
- `AlertResolvedV1` en `alerts.resolved.v1` (key: `alert_id`).

## 5. Endpoints
- `GET /api/v1/alerts` — lista con filtros `status` y `priority`, paginación (`limit`, `offset`).
- `GET /api/v1/alerts/{id}` — detalle.
- `PATCH /api/v1/alerts/{id}/assign` — `{ "analyst_id": "<uuid>" }` (OPEN → IN_REVIEW).
- `PATCH /api/v1/alerts/{id}/resolve` — `{ "resolution_notes": "..." }` (IN_REVIEW → RESOLVED).
- `PATCH /api/v1/alerts/{id}/dismiss` — `{ "reason": "..." }` (IN_REVIEW → DISMISSED).
- `GET /health`, `GET /ready` — probes.

## 6. Reglas específicas
- `ALERT_OUTBOX_RELAY_ENABLED=false` y `ALERT_CONSUMER_ENABLED=false` arrancan en `false`: se encienden cuando Kafka esté arriba.
- Un `TransactionScoredV1` con `decision=APPROVE` no genera alerta — se descarta idempotente (el consumer marca el `message_id` en `processed_events`).
- `decision=BLOCK` o `REVIEW` → alerta creada en estado `OPEN`.
- Resolver o descartar exigen que la alerta esté `IN_REVIEW`.
- `resolution_notes` y `reason` no pueden ser vacíos (validación de dominio).
- `analyst_id` es un UUID (sin autenticación real todavía; va el valor crudo).

## 7. Referencias
- Historias: US-09 (consumo + priorización), US-10 (ciclo de vida), US-11 (listado y filtros).
- ADRs: ADR-005 (id por dominio), ADR-006 (Outbox + idempotencia), ADR-004 (postgres por servicio).
