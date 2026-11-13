# alert-service

Bounded context de **Alertas** de FraudShield. Consume `TransactionScoredV1`, genera alertas (OPEN) con prioridad derivada del `risk_score`, y gestiona el ciclo de vida (`IN_REVIEW`, `RESOLVED`, `DISMISSED`) desde una API REST para el analista. Publica `AlertRaisedV1` y `AlertResolvedV1` vía Outbox.

Ver [`CLAUDE.md`](CLAUDE.md) para la guía de agentes.

## Requisitos

- Python 3.12
- Poetry 2.x
- Docker Desktop (opcional, para integración y para arrancar Postgres local)

## Setup

```bash
cd services/alert-service
poetry config virtualenvs.in-project true
poetry install
cp .env.example .env            # ajusta si hace falta
```

## Correr la verificación

```bash
poetry run ruff check .
poetry run mypy src
poetry run lint-imports
poetry run pytest -q            # 60 passed, 5 skipped (docker)
```

## Arrancar el servicio

```bash
# Con Postgres arriba via infra/docker-compose
docker compose -f ../../infra/docker-compose.yml up -d
poetry run alembic upgrade head
poetry run uvicorn alert.main:app --port 8003
curl http://localhost:8003/health
```

## Ciclo de vida de una alerta

Mientras Kafka esté apagado, se puede sembrar una alerta directamente en Postgres o esperar a que el consumer entre en línea. Una vez existe:

```bash
# listar
curl 'http://localhost:8003/api/v1/alerts?status=OPEN&priority=HIGH&limit=50'

# detalle
curl http://localhost:8003/api/v1/alerts/<alert-id>

# OPEN -> IN_REVIEW
curl -X PATCH http://localhost:8003/api/v1/alerts/<alert-id>/assign \
  -H "Content-Type: application/json" \
  -d '{"analyst_id": "11111111-1111-1111-1111-111111111111"}'

# IN_REVIEW -> RESOLVED
curl -X PATCH http://localhost:8003/api/v1/alerts/<alert-id>/resolve \
  -H "Content-Type: application/json" \
  -d '{"resolution_notes": "confirmed fraud, card cancelled"}'

# IN_REVIEW -> DISMISSED
curl -X PATCH http://localhost:8003/api/v1/alerts/<alert-id>/dismiss \
  -H "Content-Type: application/json" \
  -d '{"reason": "false positive, legitimate purchase"}'
```

Las transiciones inválidas (ej. `resolve` sobre OPEN, `dismiss` sobre RESOLVED) devuelven **409 Problem Details** con el motivo exacto.

## Mapeo `score -> priority` (ADR local)

| risk_score | priority |
| --- | --- |
| 90..100 | CRITICAL |
| 75..89 | HIGH |
| 50..74 | MEDIUM |
| 0..49 | LOW |

## Variables de entorno

Prefijo `ALERT_` (ver `.env.example`):

- `ALERT_DATABASE_URL`
- `ALERT_KAFKA_BOOTSTRAP_SERVERS`
- `ALERT_OUTBOX_RELAY_ENABLED` — enciende el relay hacia Kafka.
- `ALERT_CONSUMER_ENABLED` — enciende el consumer de `transactions.scored.v1`.
- `ALERT_CONSUMER_TOPIC` / `ALERT_CONSUMER_GROUP`.
