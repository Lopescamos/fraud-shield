# Estado — analytics-service

## Resumen (una línea)
Servicio operativo como CQRS read-side para Power BI: proyecta los cuatro eventos del dominio en dos tablas desnormalizadas (`transactions_view`, `alerts_view`), expone una API REST de solo lectura protegida por API key y calcula métricas diarias/resumen con queries agregadas al vuelo. Consumer de Kafka apagado por configuración.

## Último avance
- 2026-11-14: scaffold Poetry + Dockerfile + alembic.ini + `.env.example` + `.importlinter` + `CLAUDE.md` del servicio con el disclaimer de que esta es una excepción deliberada al DDD con agregados ricos usado en los otros tres servicios.
- 2026-11-14: kernel reducido — `Result`/`ApplicationError`, `Ids`, `IdempotentExecutor`. Sin `AbstractDomainAggregateRoot` ni `@transactional` (los proyectores manejan sesión y transacción explícitamente para escribir el marker en la misma transacción que el UPSERT).
- 2026-11-14: capa `domain` — vistas (`TransactionView`, `AlertView`), métricas (`DailyMetric`, `SummaryMetric`), VOs duplicados (`RiskScore`, `Decision`, `AlertStatus`, `Priority`), queries con validaciones (`ListTransactionsQuery`, `ListAlertsQuery`, `GetDailyMetricsQuery`, `GetSummaryMetricsQuery`) y los dos puertos `AnalyticsReadRepository` (solo queries) y `AnalyticsProjectionRepository` (cuatro UPSERTs idempotentes).
- 2026-11-14: tests unit de dominio (19 tests) — invariantes de VOs, defaults de las vistas (los campos de scoring/cierre nacen en None), invariantes de queries (limit 1..1000, offset ≥ 0, rangos de fecha no invertidos).
- 2026-11-14: capa `application` — `ProjectionApplicationServiceImpl` con cuatro métodos uno por evento (cada uno envuelve el UPSERT en `IdempotentExecutor.run_once(message_id, consumer_group, op)` dentro de la misma `session.begin()`, y mapea excepciones a `Failure`). `QueryApplicationServiceImpl` mapea a DTOs planos (`TransactionDTO`, `AlertDTO`, `DailyMetricDTO`, `SummaryMetricDTO`).
- 2026-11-14: tests unit de aplicación (10 tests) con fakes de session/proyection/read/processed-event — happy path, delivery duplicada = no-op, scored tras received completa sin pisar los campos base, alert raised→resolved, filtros forwardeados al repo, `Failure` en fallos.
- 2026-11-14: capa `infrastructure/persistence` — `Base`, entities (`TransactionViewEntity`, `AlertViewEntity`, `ProcessedEventEntity`), `AnalyticsProjectionRepositoryImpl` con cuatro UPSERTs `on_conflict_do_update` keyed por `transaction_id`/`alert_id`, `AnalyticsReadRepositoryImpl` con filtros+paginación y agregaciones SQL on-the-fly para `daily_metrics` y `summary_metrics`, `ProcessedEventStoreImpl`. Settings `ANALYTICS_*` con CSV `api_keys`, logging JSON.
- 2026-11-14: migración Alembic `V1__create_analytics_schema.py` con las tres tablas e índices (por `occurred_at`/`decision`/`country` en transactions_view; por `opened_at`/`status`/`priority` en alerts_view).
- 2026-11-14: consumer — `EventDispatcherConsumer` escucha los 4 topics sobre un solo `AIOKafkaConsumer`, dispatchea por topic, usa `shared_contracts.Envelope[...]` para validar y mapea a los `*Input` del application layer. `_decision_from_score` duplica ADR-007 porque `TransactionScoredV1` no trae `decision` cruda. `dispatch(topic, raw)` para tests sin Kafka. Desactivado por `ANALYTICS_CONSUMER_ENABLED=false`.
- 2026-11-14: capa `interfaces/rest` — resources planos; `AnalyticsController` con `GET /analytics/transactions` (filtros date_from/date_to/decision/country + paginación), `GET /analytics/alerts`, `GET /analytics/metrics/daily`, `GET /analytics/metrics/summary`; middleware `api_key.register(app, set)` protege todo menos `/health|/ready|/docs|/openapi.json|/redoc` y responde 401 Problem Details si falta/no coincide `X-API-Key`. Health y ready expuestos.
- 2026-11-14: `main.py` arma engine, session_factory, projection_service (con `AnalyticsProjectionRepositoryImpl` + `ProcessedEventStoreImpl` por sesión) y query_service (`AnalyticsReadRepositoryImpl`), registra middleware/handlers y los routers; `uvicorn analytics.main:app --port 8004`.
- 2026-11-14: tests de contrato (4) — envelopes de los cuatro eventos consumidos roundtripean y toleran campos nuevos. Tests de integración (6) con testcontainers Postgres (auto-skip si no hay Docker). Test de arquitectura (1) — import-linter: 3 contratos verdes.

## Pendiente (orden sugerido)
- [ ] Encender `ANALYTICS_CONSUMER_ENABLED=true` cuando Kafka esté arriba.
- [ ] Levantar Postgres con `docker compose -f infra/docker-compose.yml up -d` para correr los tests de integración y `poetry run alembic upgrade head`.
- [ ] Conectar Power BI al endpoint real (conector Web/JSON) con la clave de `ANALYTICS_API_KEYS`; validar que los campos planos se mapean bien en el reporte.
- [ ] CI: añadir un job de `analytics-service` al pipeline del monorepo (ruff + mypy + lint-imports + pytest).
- [ ] Rotación/gestión de API keys: hoy viven en una env var CSV; evaluar si queremos un storage (Secrets Manager / Vault) cuando haya más consumidores aparte de Power BI.

## Bloqueos / dudas
- ninguno

## Decisiones locales
- 2026-11-14: **CQRS read-side sin agregados ricos** — este servicio no tiene reglas de negocio propias. `domain/` contiene vistas y value objects reutilizados; no hay `AbstractDomainAggregateRoot`, no se emiten eventos de dominio propios y no hay patrón Outbox (es consumidor terminal). Documentado en `CLAUDE.md` del servicio y en el `README.md`.
- 2026-11-14: `daily_metrics` y `summary_metrics` se calculan on-the-fly con queries agregadas (`GROUP BY CAST(occurred_at AS DATE)` + `CASE`), no se materializa una tabla `daily_metrics`. Volumen esperado en el MVP permite calcular bajo demanda; si crece, migra a vista materializada con un job de refresh.
- 2026-11-14: autenticación por **API key en header `X-API-Key`**, claves cargadas desde `ANALYTICS_API_KEYS` (CSV). Middleware ASGI bloquea todo menos `/health|/ready|/docs|/openapi.json|/redoc` con 401 Problem Details. Decisión intencional por el ADR-008 (Power BI via API): el analítico no toca bases directas.
- 2026-11-14: UPSERT por business id (`transaction_id`, `alert_id`) + marker en `processed_events` (PK `message_id, consumer_group`) en la misma transacción. Los proyectores pueden recibir mensajes en cualquier orden (scored antes que received, resolved antes que raised) sin perder datos; los campos no-provistos mantienen lo que ya hubiera.
- 2026-11-14: `EventDispatcherConsumer._decision_from_score` duplica los umbrales ADR-007 del scoring-service porque `TransactionScoredV1` trae `score`+`level` pero no `decision` cruda. Si esos umbrales cambian, hay que actualizar las dos copias o promover `decision` a campo del contrato (ver `state/pendientes.md`).
- 2026-11-14: poetry.lock versionado para reproducibilidad del CI.
- 2026-11-14: los 6 tests de integración (testcontainers Postgres) se auto-skipean si Docker Desktop no está arriba — el entorno local actual no lo está; una vez arriba, corren sin cambios.
