# Estado — scoring-service

## Resumen (una línea)
Servicio operativo para calcular el puntaje de fraude de una transacción combinando reglas + XGBoost + Isolation Forest + SHAP, con degradación agraciada a solo reglas, persistencia en `scoring.*` y publicación de `TransactionScoredV1` vía Outbox (relay a Kafka y consumer apagados por configuración).

## Último avance
- 2026-11-13: scaffold Poetry + Dockerfile + alembic.ini + `.env.example` + `.importlinter` (incluye xgboost/sklearn/shap como prohibidos para domain/application) + `CLAUDE.md` del servicio.
- 2026-11-13: kernel completo (duplicado del de transaction-service): `Result`/`ApplicationError`, `@transactional`, `AbstractDomainAggregateRoot`, `EventDispatcher`, `Ids`, `IdempotentExecutor`.
- 2026-11-13: capa `domain` — aggregate `ScoringResult` (`register`/`restore`), VOs `RiskScore`/`Decision`/`ModelVersion`/`RiskFactor`, command `ScoreTransactionCommand`, query `GetScoringResultByIdQuery`, evento `ScoringResultRegisteredEvent`, puerto `ScoringResultRepository`, puertos de servicios (`RuleCatalog`, `RiskModel`, `Explainer`, `ModelRegistry`).
- 2026-11-13: tests unit de dominio (18 tests) — rangos de `RiskScore`, umbrales ADR-007 de `Decision` y `level_from_score`, `ModelVersion`/`RiskFactor` validaciones, `ScoringResult.register` emite evento con score/decision/level correctos, `restore` no emite evento, modo degradado usa `rules-only`.
- 2026-11-13: capa `application` — `ScoringApplicationServiceImpl` orquesta reglas → modelos ML (con degradación en cualquier fallo) → combinación ponderada → SHAP top-3 (solo si no hay degradación) → persistencia; `Result[UUID, ApplicationError]`; `@transactional`; idempotencia por `transaction_id`. `ScoringResultQueryServiceImpl` para GET. Puerto `MessagePublisher` y `RuleEngine`. `ScoringResultRegisteredEventHandler` traduce el evento de dominio a `TransactionScoredV1` sobre `transactions.scored.v1`.
- 2026-11-13: tests unit de aplicación (7 tests) con `FakeSession`/`FakeScoringResultRepository` y puertos fake — happy path, degradación por modelos no disponibles, combinación `0.4 rules + 0.4 * 100 * p_xgb + 0.2 * 100 * a_iso`, idempotencia por `transaction_id`, rollback cuando reglas revientan, degradación por excepción del modelo, explainer no se invoca en modo degradado, rollback cuando el repo falla en save.
- 2026-11-13: motor de reglas YAML — `rules.yaml` con cinco reglas iniciales (`atypical_amount` por canal, `high_risk_country`, `unusual_hour`, `new_device`, `velocity`), `YamlRuleCatalog` carga y cachea, `CatalogRuleEngine` evalúa y satura el score en 100. 7 tests unit.
- 2026-11-13: adaptadores ML con degradación — `XGBoostRiskModel.load_or_degrade`, `IsolationForestRiskModel.load_or_degrade`, `ShapExplainer.from_booster(None)` siempre devuelven `is_available()=False` cuando la ruta está vacía / el archivo no existe / `load()` revienta; `features.vectorize(command)` compartido. 9 tests unit.
- 2026-11-13: capa `infrastructure/persistence` — `Base`, `ScoringResultPersistenceEntity` (índice unique por `transaction_id`), `ModelRegistryPersistenceEntity`, `ProcessedEventPersistenceEntity` (PK compuesta), `OutboxPersistenceEntity`, assembler y `ScoringResultRepositoryImpl` que despacha `pull_events()` en `save()`. `ModelRegistryAdapter` y `ProcessedEventStoreImpl`. Settings `SCORING_*` con rutas de modelos y pesos configurables, logging JSON.
- 2026-11-13: migración Alembic `V1__create_scoring_schema.py` — tablas `scoring.scoring_results` (con índice único por `transaction_id`), `scoring.model_registry`, `scoring.outbox_events`, `scoring.processed_events`.
- 2026-11-13: outbox — `OutboxMessagePublisher` escribe fila PENDING en `scoring.outbox_events` usando la misma sesión; `KafkaBrokerPublisher` (aiokafka, import lazy); `OutboxRelay` asyncio con `FOR UPDATE SKIP LOCKED`, marca `PUBLISHED`/`FAILED` tras 5 intentos. Desactivado por `SCORING_OUTBOX_RELAY_ENABLED=false`.
- 2026-11-13: consumer — `TransactionReceivedConsumer` escucha `transactions.received.v1` (grupo `scoring.assess-transaction`), valida `Envelope[TransactionReceivedV1]`, traduce a `ScoreTransactionCommand` y entra por el application service. Idempotencia doble (processed_events + transaction_id). `handle_payload(raw)` expone el pipeline sin Kafka para tests. Desactivado por `SCORING_CONSUMER_ENABLED=false`.
- 2026-11-13: capa `interfaces/rest` — resources (entrada con `extra='forbid'`, salida con factores), transforms, `ScoresController` (POST `/api/v1/scores` 202 con `Idempotency-Key`, GET `/api/v1/scores/{id}`), `/health` y `/ready`, exception handlers con Problem Details RFC 7807 y `trace_id`. 7 tests de controller.
- 2026-11-13: `main.py` compone todo (settings, engine, repository_builder por sesión, rule engine YAML, modelos con `load_or_degrade`, SHAP desde el booster XGB, pesos configurables); logea `scoring-service-degraded` si falta algún modelo; `uvicorn scoring.main:app --port 8002` arranca y responde `/health`.
- 2026-11-13: tests de contrato (3) — `Envelope[TransactionScoredV1]` roundtrip y tolerancia a campos nuevos. Tests de integración (4) con testcontainers (auto-skip sin Docker). Test de arquitectura (1) — import-linter: 3 contratos verdes. Total: 69 passed, 4 skipped; ruff y mypy limpios.

## Pendiente (orden sugerido)
- [ ] Entrenar modelos reales: ejecutar `scripts/train_xgboost.py` y `scripts/train_isolation_forest.py` cuando el agente `ml` los escriba; guardar las rutas en `SCORING_XGB_MODEL_PATH` y `SCORING_IFOREST_MODEL_PATH` y registrar la versión activa en `scoring.model_registry`.
- [ ] Encender `OutboxRelay` + `KafkaBrokerPublisher` cuando Kafka esté arriba (`SCORING_OUTBOX_RELAY_ENABLED=true`).
- [ ] Encender `TransactionReceivedConsumer` cuando Kafka esté arriba (`SCORING_CONSUMER_ENABLED=true`) y dejar de depender del POST `/api/v1/scores` manual.
- [ ] Levantar Postgres con `docker compose -f infra/docker-compose.yml up -d` para correr los tests de integración y `poetry run alembic upgrade head`.
- [ ] CI: añadir un job de `scoring-service` al pipeline del monorepo (ruff + mypy + lint-imports + pytest).
- [ ] Scripts `scripts/train_*.py` + `scripts/evaluate_model.py` con PR-AUC y puerta de calidad (RNF-23 / ADR-007).

## Bloqueos / dudas
- ninguno

## Decisiones locales
- 2026-11-13: ingestión por REST manual (`POST /api/v1/scores`) además del consumer de Kafka; mientras Kafka esté apagado es la única forma de probar el flujo end-to-end. El consumer queda implementado pero `SCORING_CONSUMER_ENABLED=false`.
- 2026-11-13: motor de reglas vive en `infrastructure/rules/catalog_rule_engine.py` como adaptador del puerto `RuleEngine` (definido en `application/internal/outboundservices/rules/`), para que `domain` no sepa de YAML.
- 2026-11-13: idempotencia por `transaction_id` en el `ScoringApplicationServiceImpl` (devuelve el `scoring_result_id` existente), respaldada por índice `unique` en `scoring.scoring_results.transaction_id`. La cabecera HTTP `Idempotency-Key` se acepta y se logea, pero la idempotencia dura es por `transaction_id`.
- 2026-11-13: la combinación del puntaje final vive en `application` (ADR-007). Pesos iniciales `0.4 / 0.4 / 0.2` configurables por env (`SCORING_WEIGHT_*`). El resultado se satura a `0..100`.
- 2026-11-13: SHAP solo se calcula cuando ningún modelo degradó; si el explainer revienta, se descartan los factores SHAP y se guardan solo los `RiskFactor` de reglas (no se rompe el flujo).
- 2026-11-13: `scoring.scoring_results.factors` se almacena como JSONB (lista de `{feature, weight, direction, source}`) en lugar de una tabla aparte `shap_factors`: simplifica la migración inicial y basta para el MVP; una historia futura puede normalizar.
- 2026-11-13: `type: ignore[import-untyped]` sobre `import yaml` en `yaml_rule_catalog.py` porque `pyyaml` no publica stubs oficiales.
- 2026-11-13: poetry.lock versionado para reproducibilidad del CI.
- 2026-11-13: los 4 tests de integración (testcontainers Postgres) se auto-skipean si Docker Desktop no está arriba — el entorno local actual no lo está; una vez arriba, correrán sin cambios.
