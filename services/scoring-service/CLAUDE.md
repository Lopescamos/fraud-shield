# scoring-service — CLAUDE.md

## 1. Rol en el sistema
Bounded context de **Scoring**. Toma una transacción (recibida por REST manual mientras Kafka está apagado; en el futuro por el topic `transactions.received.v1`), combina reglas + Isolation Forest + XGBoost, explica el resultado con SHAP, persiste el `ScoringResult` y publica `TransactionScoredV1` por el patrón Outbox.

## 2. Lenguaje ubicuo
- **ScoringResult**: aggregate con `id` UUID generado por el dominio, puntaje `0–100`, `decision` derivada de umbrales y `model_version`.
- **RiskScore**: VO `float 0..100`.
- **Decision**: enum `APPROVE | REVIEW | BLOCK`, derivada del score por umbrales.
- **ModelVersion**: VO con el identificador del modelo activo (o `rules-only` en modo degradado).
- **RiskFactor**: VO `(feature, weight, direction)` para los top-3 de SHAP.
- **Rules engine**: catálogo YAML de reglas simples (monto umbral, país alto riesgo, hora inusual, etc.).
- **Outbox**: tabla `scoring.outbox_events` escrita en la misma transacción que la persistencia del aggregate.
- **Processed events**: tabla `scoring.processed_events` para idempotencia del consumer y por `transaction_id`.
- **model_registry**: tabla `scoring.model_registry` con la fila activa (`is_active=true`).

## 3. Agregados
- `ScoringResult` — inmutable una vez calculado. Expone `register(...)` (crea `id`, emite `ScoringResultRegisteredEvent`) y `restore(...)` (reconstrucción sin eventos).

## 4. Mensajes
### Consume
- `TransactionReceivedV1` (topic `transactions.received.v1`, grupo `scoring.assess-transaction`) — consumer presente pero **desactivado** por `SCORING_CONSUMER_ENABLED=false` hasta que Kafka esté arriba.
### Publica
- `TransactionScoredV1` en `transactions.scored.v1` (key: `account_id_hash`).

## 5. Endpoints
- `POST /api/v1/scores` — ingestión manual de una transacción para scoring (202). Soporta `Idempotency-Key` y además idempotencia por `transaction_id`.
- `GET /api/v1/scores/{id}` — devolver el resultado por `scoring_result_id`.
- `GET /health`, `GET /ready` — probes.

## 6. Reglas específicas
- `SCORING_OUTBOX_RELAY_ENABLED` arranca en `false`: el relay a Kafka se enciende cuando Kafka esté disponible.
- `SCORING_CONSUMER_ENABLED` arranca en `false`: el consumer de Kafka queda implementado pero apagado.
- **Degradación**: si `SCORING_XGB_MODEL_PATH` o `SCORING_IFOREST_MODEL_PATH` están vacíos o el archivo no existe, el servicio arranca igual, calcula el score **solo con reglas** y marca `degraded_mode=true`.
- Umbrales (ADR-007): 0–39 LOW/APPROVE, 40–69 MEDIUM/REVIEW, 70–89 HIGH/REVIEW, 90–100 CRITICAL/BLOCK.
- Pesos iniciales de combinación: `0.4 * rules + 0.4 * 100 * p_xgb + 0.2 * 100 * a_iforest` (configurable por env).
- El `account_id` se guarda **solo como hash** (SHA-256) en todas las tablas y eventos.

## 7. Referencias
- Historias: US-05, US-06, US-07, US-08 (scoring, explicabilidad, degradación).
- ADRs: ADR-005 (id por dominio), ADR-006 (Outbox + idempotencia), ADR-007 (reglas + ML + SHAP), ADR-004 (postgres por servicio).
