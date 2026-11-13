# Estado — transaction-service

## Resumen (una línea)
Servicio operativo para registrar y consultar transacciones por API con idempotencia por header y publicación de `TransactionReceivedV1` vía Outbox (relay a Kafka apagado).

## Último avance
- 2026-11-12: scaffold Poetry + Dockerfile + alembic.ini + `.env.example` + `.importlinter` + `CLAUDE.md` del servicio.
- 2026-11-12: kernel completo (`Result`/`ApplicationError`, `@transactional`, `AbstractDomainAggregateRoot`, `EventDispatcher`, `Ids`, `IdempotentExecutor`).
- 2026-11-12: capa `domain` — aggregate `Transaction` (`register`/`restore`), VOs `AccountId`/`Money`/`Channel`, command `RegisterTransactionCommand`, query `GetTransactionByIdQuery`, evento `TransactionRegisteredEvent`, puerto `TransactionRepository`.
- 2026-11-12: capa `infrastructure` — `Base`, `TransactionPersistenceEntity`, `IdempotencyKeyPersistenceEntity`, `OutboxPersistenceEntity`, `TransactionPersistenceAssembler`, `TransactionRepositoryImpl`, `OutboxMessagePublisher`, settings y logging JSON.
- 2026-11-12: migración Alembic `V1__create_tx_schema.py` (tablas `tx.transactions` con índice `(account_id_hash, occurred_at DESC)`, `tx.outbox_events`, `tx.idempotency_keys`).
- 2026-11-12: capa `application` — `TransactionCommandService`/`Impl` con `Result` y `@transactional`, `TransactionQueryService`/`Impl`, `MessagePublisher` (puerto), `TransactionRegisteredEventHandler` que emite `TransactionReceivedV1` por el canal `transactions.received.v1`.
- 2026-11-12: capa `interfaces/rest` — resources (entrada/salida/202), transforms, `TransactionsController` (POST/GET), `/health` y `/ready`, exception handlers con Problem Details RFC 7807.
- 2026-11-12: `main.py` compone todo (settings, engine, repository_builder por sesión, servicios en `app.state`); `uvicorn transaction.main:app --port 8001` arranca y responde `/health`.
- 2026-11-12: tests — 12 unit (domain + application con fakes), 3 contract (envelope roundtrip + tolerancia), 7 interfaces/rest (POST 202/422, GET 200/404, idempotency, /health), 1 architecture (import-linter: 3 contratos verdes), 3 integration de persistencia que se skipean limpiamente cuando Docker no está disponible.

## Pendiente (orden sugerido)
- [ ] US-02 — endpoint `POST /api/v1/transactions/batch` (lote hasta 500).
- [ ] Encender `OutboxRelayJob` + `KafkaBrokerPublisher` cuando Kafka esté arriba (`TRANSACTION_OUTBOX_RELAY_ENABLED=true`).
- [ ] Levantar Postgres con `docker compose -f infra/docker-compose.yml up -d` para correr los tests de integración y `poetry run alembic upgrade head`.
- [ ] CI: añadir un job de `transaction-service` al pipeline del monorepo (ruff + mypy + lint-imports + pytest).

## Bloqueos / dudas
- ninguno

## Decisiones locales
- 2026-11-12: `tx.transactions` usa `UUID` como PK directa (siguiendo la indicación explícita de la tarea y la guía del agente `infrastructure`), en vez del combo `BIGSERIAL PK + UUID UNIQUE` sugerido en `docs/modelo-datos.md` §1.1. El ADR-005 se cumple: el `id` sigue siendo generado por el dominio y viaja en eventos y API.
- 2026-11-12: `channel` se almacena como `VARCHAR(16)` y el Assembler hace la conversión al enum `Channel`, para no crear un tipo ENUM de Postgres en la migración.
- 2026-11-12: el test de arquitectura invoca `importlinter.cli.lint_imports_command` por `subprocess` con `encoding="utf-8"` para evitar un `UnicodeDecodeError` en Windows (cp1252) cuando el banner ASCII art usa caracteres no-ANSI.
- 2026-11-12: `poetry.lock` versionado para reproducibilidad del CI.
- 2026-11-12: los 3 tests de integración (testcontainers Postgres) se auto-skipean si Docker Desktop no está arriba — el entorno local actual no lo está; una vez arriba, correrán sin cambios.
