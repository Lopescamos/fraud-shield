# Estado — alert-service

## Resumen (una línea)
Servicio operativo para generar alertas automáticas a partir de `TransactionScoredV1`, gestionar su ciclo de vida (OPEN → IN_REVIEW → RESOLVED/DISMISSED) desde una API REST para analistas, con persistencia en `alerts.*` y publicación de `AlertRaisedV1` + `AlertResolvedV1` vía Outbox (relay a Kafka y consumer apagados por configuración).

## Último avance
- 2026-11-13: scaffold Poetry + Dockerfile + alembic.ini + `.env.example` + `.importlinter` + `CLAUDE.md` del servicio.
- 2026-11-13: kernel completo (duplicado): `Result`/`ApplicationError`, `@transactional`, `AbstractDomainAggregateRoot`, `EventDispatcher`, `Ids`, `IdempotentExecutor`.
- 2026-11-13: capa `domain` — aggregate `Alert` con `register`/`assign`/`resolve`/`dismiss`/`restore`; VOs `AlertId`, `AlertStatus` (OPEN/IN_REVIEW/RESOLVED/DISMISSED con `is_terminal`), `Priority` (LOW/MEDIUM/HIGH/CRITICAL con `from_risk_score` y umbrales `>=50/>=75/>=90`), `RiskFactor` duplicado. Commands (`RaiseAlertFromScoreCommand`, `AssignAlertCommand`, `ResolveAlertCommand`, `DismissAlertCommand`), queries (`ListAlertsQuery`, `GetAlertByIdQuery`), eventos (`AlertRaisedEvent`, `AlertResolvedEvent`), excepción `InvalidAlertTransition`, puerto `AlertRepository`.
- 2026-11-13: tests unit de dominio (34 tests) — umbrales de `Priority`, invariantes de VOs, todas las transiciones válidas e inválidas del aggregate, texto obligatorio en resolve/dismiss, `restore` no emite eventos.
- 2026-11-13: capa `application` — `AlertApplicationServiceImpl` con `raise_from_score` (APPROVE → no-op, idempotencia por `transaction_id`), `assign`/`resolve`/`dismiss` (mapea `InvalidAlertTransition` a `business_rule_violation`); `AlertQueryServiceImpl` para list/get. Handlers `AlertRaisedEventHandler` y `AlertResolvedEventHandler` traducen a `AlertRaisedV1`/`AlertResolvedV1` en los canales `alerts.raised.v1` y `alerts.resolved.v1`.
- 2026-11-13: tests unit de aplicación (10 tests) con `FakeAlertRepository` + `FakeSession` — happy path, APPROVE no-op, idempotencia por `transaction_id`, transiciones, notas vacías → `validation_error`, alert inexistente → `not_found`, rollback en fallo de repo.
- 2026-11-13: capa `infrastructure/persistence` — `Base`, `AlertPersistenceEntity` (índice `unique` por `transaction_id` + índices `(status, opened_at DESC)` y `(priority, opened_at DESC)` para los listados), `ProcessedEventPersistenceEntity` (PK compuesta), `OutboxPersistenceEntity`. Assembler usa `restore()`. `AlertRepositoryImpl` hace `upsert` en `save()` (`on_conflict_do_update`) para permitir avanzar el status del mismo aggregate sin tocar `transaction_id`/`opened_at`, despacha `pull_events()` via `EventDispatcher`. `ProcessedEventStoreImpl` para idempotencia del consumer.
- 2026-11-13: migración Alembic `V1__create_alerts_schema.py` con las tres tablas y sus índices.
- 2026-11-13: outbox — `OutboxMessagePublisher` (fila PENDING en misma sesión), `KafkaBrokerPublisher` (aiokafka lazy), `OutboxRelay` asyncio con `FOR UPDATE SKIP LOCKED` y hasta 5 reintentos. Desactivado por `ALERT_OUTBOX_RELAY_ENABLED=false`.
- 2026-11-13: consumer — `TransactionScoredConsumer` escucha `transactions.scored.v1` (grupo `alert.raise-on-scored`), valida `Envelope[TransactionScoredV1]`, infiere `decision` desde el `score` con los umbrales ADR-007 duplicados, construye `RaiseAlertFromScoreCommand` y entra por el application service. Idempotencia doble. `handle_payload(raw)` expone el pipeline para tests. Desactivado por `ALERT_CONSUMER_ENABLED=false`.
- 2026-11-13: capa `interfaces/rest` — resources con `extra="forbid"` para las acciones; controllers `GET /api/v1/alerts` (filtros, paginación), `GET /api/v1/alerts/{id}`, `PATCH /api/v1/alerts/{id}/assign|resolve|dismiss`, `/health`, `/ready`. Exception handlers RFC 7807 con `trace_id` mapean `business_rule_violation` → 409 y `not_found` → 404. 10 tests de controller.
- 2026-11-13: `main.py` compone todo (settings, engine, repository_builder por sesión que arma OutboxMessagePublisher + los dos event handlers + dispatcher, servicios en `app.state`); `uvicorn alert.main:app --port 8003`.
- 2026-11-13: tests de contrato (5) — constantes versionadas, `Envelope[AlertRaisedV1]`/`Envelope[AlertResolvedV1]` roundtrip + tolerancia + variante DISMISSED. Tests de integración (5) con testcontainers (auto-skip sin Docker). Test de arquitectura (1) — import-linter: 3 contratos verdes. Total: 60 passed, 5 skipped; ruff y mypy limpios.

## Pendiente (orden sugerido)
- [ ] Autenticación real de analistas (`analyst_id` sale del token JWT) cuando exista `api-gateway`.
- [ ] Encender `OutboxRelay` + `KafkaBrokerPublisher` cuando Kafka esté arriba (`ALERT_OUTBOX_RELAY_ENABLED=true`).
- [ ] Encender `TransactionScoredConsumer` cuando Kafka esté arriba (`ALERT_CONSUMER_ENABLED=true`).
- [ ] Levantar Postgres con `docker compose -f infra/docker-compose.yml up -d` para correr los tests de integración y `poetry run alembic upgrade head`.
- [ ] CI: añadir un job de `alert-service` al pipeline del monorepo (ruff + mypy + lint-imports + pytest).
- [ ] Reasignación de alerta (US futuro): actualmente `assign` solo opera sobre OPEN; evaluar si una alerta IN_REVIEW puede cambiar de analista.

## Bloqueos / dudas
- ninguno

## Decisiones locales
- 2026-11-13: umbrales de `Priority.from_risk_score` (inclusivos): `>=90` CRITICAL, `>=75` HIGH, `>=50` MEDIUM, resto LOW. Rechaza `score` fuera de 0..100.
- 2026-11-13: `assign` solo opera sobre `OPEN`; `resolve`/`dismiss` solo sobre `IN_REVIEW`. Cualquier otra transición lanza `InvalidAlertTransition` y la capa application la convierte a `Failure(ApplicationError.business_rule_violation(...))` (HTTP 409 por los exception handlers).
- 2026-11-13: `resolution_notes` y `reason` son invariantes de dominio (texto no vacío) + validados en Pydantic con `min_length=1` para que el 422 lo capture la capa REST antes de bajar al dominio.
- 2026-11-13: `AlertRepositoryImpl.save` hace `on_conflict_do_update` sobre el PK `id`, ignorando `transaction_id` y `opened_at`. Esto permite que el mismo aggregate avance su `status` sin crear una fila nueva (la PK la pone el dominio).
- 2026-11-13: `TransactionScoredConsumer._decision_from_score` duplica los umbrales de `scoring-service` (ADR-007: APPROVE<40, REVIEW 40..89, BLOCK>=90) porque este servicio no depende del paquete `scoring`. Si esos umbrales cambian, se actualizan en los dos sitios o se mueve `decision` al payload de `TransactionScoredV1` como campo propio.
- 2026-11-13: `analyst_id` se recibe como UUID crudo en los PATCH, sin autenticación. La `api-gateway` futura lo sacará del JWT; mientras tanto el endpoint sirve.
- 2026-11-13: `factors` en `alerts.alerts` se guarda como JSONB (igual que en scoring-service) en lugar de una tabla normalizada.
- 2026-11-13: poetry.lock versionado para reproducibilidad del CI.
- 2026-11-13: los 5 tests de integración (testcontainers Postgres) se auto-skipean si Docker Desktop no está arriba — el entorno local actual no lo está.
