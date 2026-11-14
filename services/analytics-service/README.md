# analytics-service

Bounded context de **Analítica** de FraudShield. Es la cara de **lectura** del sistema (CQRS read-side): consume los cuatro eventos de integración (`TransactionReceivedV1`, `TransactionScoredV1`, `AlertRaisedV1`, `AlertResolvedV1`), los proyecta en dos tablas desnormalizadas y expone una API REST de solo lectura protegida por API key, pensada para que Power BI la consuma vía el conector Web/JSON.

Ver [`CLAUDE.md`](CLAUDE.md) para la guía de agentes.

## Por qué este servicio no sigue DDD con agregados ricos

Los otros tres servicios del repo (`transaction-service`, `scoring-service`, `alert-service`) implementan DDD con agregados ricos: aggregates con invariantes, eventos de dominio y Outbox. **`analytics-service` es una excepción deliberada**:

- No tiene reglas de negocio propias. Solo proyecta eventos ya emitidos y responde queries.
- `domain/` contiene **vistas** (sin comportamiento) y **value objects duplicados** de los otros servicios (para no depender de sus paquetes). No hay agregados.
- **No hay patrón Outbox** porque este servicio no publica eventos; es un consumidor terminal.
- El `kernel/` es reducido (`Result`, `Ids`, `IdempotentExecutor`); no incluye `AbstractDomainAggregateRoot` ni `@transactional` (los proyectores manejan sesión y transacción explícitamente para que el marker de `processed_events` y el UPSERT caigan en la misma transacción).

El forzar un agregado rico aquí daría anemia sin aportar nada: todo lo que haría el agregado es traducir el payload a columnas. El criterio es consistencia con la decisión arquitectónica, no uniformidad por sí misma.

## Requisitos

- Python 3.12
- Poetry 2.x
- Docker Desktop (opcional, para integración y para arrancar Postgres local)

## Setup

```bash
cd services/analytics-service
poetry config virtualenvs.in-project true
poetry install
cp .env.example .env            # ajusta ANALYTICS_API_KEYS
```

## Correr la verificación

```bash
poetry run ruff check .
poetry run mypy src
poetry run lint-imports
poetry run pytest -q
```

## Arrancar el servicio

```bash
# Con Postgres arriba via infra/docker-compose
docker compose -f ../../infra/docker-compose.yml up -d
poetry run alembic upgrade head
poetry run uvicorn analytics.main:app --port 8004
curl http://localhost:8004/health
```

## Consumir desde Power BI (o curl)

Todos los endpoints bajo `/analytics/*` requieren el header `X-API-Key`. Las claves válidas se cargan de `ANALYTICS_API_KEYS` (CSV).

```bash
KEY="dev-powerbi-key-change-me"

# Transacciones con filtros
curl -H "X-API-Key: $KEY" \
  'http://localhost:8004/analytics/transactions?decision=BLOCK&country=PE&limit=100'

# Alertas con filtros
curl -H "X-API-Key: $KEY" \
  'http://localhost:8004/analytics/alerts?status=OPEN&priority=CRITICAL&limit=100'

# Métricas diarias (rango obligatorio)
curl -H "X-API-Key: $KEY" \
  'http://localhost:8004/analytics/metrics/daily?date_from=2026-11-01T00:00:00Z&date_to=2026-11-30T00:00:00Z'

# Resumen acumulado
curl -H "X-API-Key: $KEY" http://localhost:8004/analytics/metrics/summary
```

En Power BI: **Get Data → Web → Advanced**, pegar la URL y agregar un header `X-API-Key` con el valor de la env var. Los campos están aplanados (`snake_case`, un solo nivel) para que la navegación en Power Query sea trivial.

Falta o clave inválida → **401 Problem Details**. `/health` y `/ready` son públicos.

## Variables de entorno

Prefijo `ANALYTICS_` (ver `.env.example`):

- `ANALYTICS_DATABASE_URL`
- `ANALYTICS_KAFKA_BOOTSTRAP_SERVERS`
- `ANALYTICS_CONSUMER_ENABLED` — enciende el `EventDispatcherConsumer`.
- `ANALYTICS_CONSUMER_GROUP` — prefijo del `group_id` de Kafka.
- `ANALYTICS_API_KEYS` — CSV con las claves que acepta el middleware.
