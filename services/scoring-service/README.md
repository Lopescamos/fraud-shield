# scoring-service

Bounded context de **Scoring** de FraudShield. Calcula el puntaje de fraude de una transacción combinando reglas, Isolation Forest y XGBoost, lo explica con SHAP, lo persiste y publica `TransactionScoredV1` vía Outbox.

Ver [`CLAUDE.md`](CLAUDE.md) para la guía de agentes.

## Requisitos

- Python 3.12
- Poetry 2.x
- Docker Desktop (opcional, para integración y para arrancar Postgres local)

## Setup

```bash
cd services/scoring-service
poetry config virtualenvs.in-project true
poetry install
cp .env.example .env            # ajusta si hace falta
```

## Correr la verificación

```bash
poetry run ruff check .
poetry run mypy src
poetry run lint-imports
poetry run pytest -q            # 69 passed, 4 skipped (docker)
```

## Arrancar el servicio

```bash
# Con Postgres arriba via infra/docker-compose
docker compose -f ../../infra/docker-compose.yml up -d
poetry run alembic upgrade head
poetry run uvicorn scoring.main:app --port 8002
curl http://localhost:8002/health
```

## Scorear una transacción (manual, mientras Kafka esté apagado)

```bash
curl -X POST http://localhost:8002/api/v1/scores \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-1" \
  -d '{
    "transaction_id": "00000000-0000-0000-0000-000000000001",
    "account_id_hash": "'"$(printf 'acc-1' | sha256sum | cut -d" " -f1)"'",
    "amount": "150.00",
    "currency": "PEN",
    "channel": "WEB",
    "occurred_at": "2026-11-13T13:45:00Z",
    "country": "PE",
    "extra_features": {"tx_count_last_5m": 1.0}
  }'
```

## Degradación

Si `SCORING_XGB_MODEL_PATH` o `SCORING_IFOREST_MODEL_PATH` están vacíos o el archivo no existe:

- `is_available()` devuelve `false` para ese modelo.
- El servicio arranca igual.
- El score se calcula **solo con reglas** y se guarda con `degraded_mode=true` y `model_version="rules-only"`.
- SHAP no se invoca.

## Variables de entorno

Prefijo `SCORING_` (ver `.env.example`):

- `SCORING_DATABASE_URL` — conexión a Postgres.
- `SCORING_KAFKA_BOOTSTRAP_SERVERS` — bootstrap servers de Kafka (sin efecto mientras los switches estén en `false`).
- `SCORING_OUTBOX_RELAY_ENABLED` — enciende el relay del Outbox hacia Kafka.
- `SCORING_CONSUMER_ENABLED` — enciende el consumer de `transactions.received.v1`.
- `SCORING_RULES_PATH` — ruta al YAML del catálogo de reglas.
- `SCORING_XGB_MODEL_PATH` / `SCORING_IFOREST_MODEL_PATH` — rutas a los modelos serializados.
- `SCORING_WEIGHT_RULES` / `SCORING_WEIGHT_XGB` / `SCORING_WEIGHT_IFOREST` — pesos de la combinación.
