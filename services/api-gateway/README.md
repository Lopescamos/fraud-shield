# api-gateway

Única puerta pública de FraudShield. Autentica analistas con **JWT** (HS256), inyecta el `analyst_id` cuando asigna alertas, y traduce el JWT a la **API key interna** cuando enruta hacia `analytics-service`. Los sistemas upstream que publican transacciones usan una **API key de posting** separada (es un flujo máquina-a-máquina).

## Mapeo de rutas

| Externo | Auth | Interno |
| --- | --- | --- |
| `POST /auth/token` | — | — (emite JWT) |
| `POST /api/v1/transactions` | `X-API-Key` posting | `transaction-service` |
| `GET /api/v1/transactions/{id}` | JWT | `transaction-service` |
| `POST /api/v1/scores` | JWT | `scoring-service` |
| `GET /api/v1/scores/{id}` | JWT | `scoring-service` |
| `GET /api/v1/alerts(?filters)` | JWT | `alert-service` |
| `GET /api/v1/alerts/{id}` | JWT | `alert-service` |
| `PATCH /api/v1/alerts/{id}/assign` | JWT | `alert-service` (**inyecta `analyst_id`** del claim) |
| `PATCH /api/v1/alerts/{id}/resolve` | JWT | `alert-service` |
| `PATCH /api/v1/alerts/{id}/dismiss` | JWT | `alert-service` |
| `GET /analytics/*` | JWT | `analytics-service` (**traduce a `X-API-Key`**) |
| `GET /health`, `GET /ready` | — | — |

## Setup

```bash
cd services/api-gateway
poetry config virtualenvs.in-project true
poetry install
cp .env.example .env
```

### Generar un hash bcrypt para tu usuario

```bash
poetry run python -c "from gateway.infrastructure.security.bcrypt_hasher import BcryptPasswordHasher; print(BcryptPasswordHasher.hash('mypassword'))"
```

Luego en `.env`:

```
GATEWAY_USERS=kevin:$2b$12$...:11111111-1111-1111-1111-111111111111
```

## Verificación

```bash
poetry run ruff check .
poetry run mypy src
poetry run lint-imports    # 3 kept, 0 broken
poetry run pytest -q       # 17 passed
```

## Arrancar

```bash
# En terminales separadas: los 4 servicios internos
poetry run uvicorn gateway.main:app --port 8000
curl http://localhost:8000/health

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"username":"kevin","password":"mypassword"}' | jq -r .access_token)

# Pedir una alerta
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/alerts
```

## Variables de entorno

Prefijo `GATEWAY_` (ver `.env.example`):

- `GATEWAY_JWT_SECRET`, `GATEWAY_JWT_ALGORITHM`, `GATEWAY_JWT_TTL_SECONDS`, `GATEWAY_JWT_ISSUER`
- `GATEWAY_USERS` — CSV `username:bcrypt_hash:analyst_uuid`.
- `GATEWAY_POSTING_API_KEY` — clave de los sistemas upstream.
- `GATEWAY_{TRANSACTION,SCORING,ALERT,ANALYTICS}_SERVICE_URL`
- `GATEWAY_ANALYTICS_API_KEY` — clave que el gateway inyecta hacia analytics-service.
- `GATEWAY_HTTP_TIMEOUT_SECONDS`
