# Contrato de API

Documento acompañante del Swagger generado por FastAPI (vive en `/docs` de cada servicio y consolidado en el gateway). Aquí quedan las **convenciones** y el **mapa de endpoints** que valen para todos los servicios.

## 1. Convenciones

| Tema | Convención |
| --- | --- |
| Rutas públicas | `/api/v1/<recurso-en-plural>` (todo bajo `/bi/v1` para Power BI) |
| Formato | JSON, campos en `snake_case` (sigue PEP 8 y lo que ya usan los contratos) |
| Fechas | ISO 8601 en UTC (`2026-11-12T13:45:00Z`) |
| Identificadores de negocio | UUID (string) |
| Montos | `amount` decimal, `currency` en código ISO 4217 (3 letras) |
| Autenticación | JWT en `Authorization: Bearer <token>` para humanos; `X-API-Key` para sistemas |
| Errores | Problem Details (RFC 7807): `type`, `title`, `status`, `detail`, `trace_id` |
| Paginación | `?page=1&page_size=50` + metadata en la respuesta |
| Versionado | En la ruta (`/api/v1`, `/bi/v1`) y en los contratos (`V1`, `V2`) |
| Trazabilidad | Cabecera `X-Trace-Id`; el gateway la genera si no viene |
| Rate limiting | `429` con `Retry-After`; cabeceras `X-RateLimit-Limit`, `X-RateLimit-Remaining` |

### 1.1 Formato de error

```json
{
  "type": "about:blank",
  "title": "Validation failed",
  "status": 422,
  "detail": "amount must be greater than zero",
  "trace_id": "01HSZK2A7F5V4N1Q4X2TB3W7PH",
  "errors": [
    { "field": "amount", "message": "must be greater than zero" }
  ]
}
```

### 1.2 Formato de respuesta paginada

```json
{
  "data": [ /* … */ ],
  "page": 1,
  "page_size": 50,
  "total_items": 1234,
  "total_pages": 25
}
```

## 2. Autenticación

### 2.1 Para analistas y administradores (JWT)

- `POST /api/v1/auth/login` — body `{"email":"…","password":"…"}` → `{"access_token","refresh_token","expires_in"}`.
- `POST /api/v1/auth/refresh` — body `{"refresh_token":"…"}` → nuevo `access_token`.
- JWT con vida de 15 minutos; refresh de 7 días.

### 2.2 Para sistemas (API key)

- Cabecera `X-API-Key: <clave>`.
- Roles disponibles: `ingest_client`, `analyst`, `admin`, `bi_reader`.
- Cada clave queda guardada por su hash; el valor se muestra **una sola vez** al crearla.
- Rotación manual por el administrador.

## 3. Endpoints por servicio

Las rutas públicas pasan todas por el `api-gateway`; detrás, cada servicio las expone en su puerto interno. El gateway añade la autenticación y la trazabilidad.

### 3.1 transaction-service — `/api/v1/transactions`

| Método | Ruta | Rol | Para qué |
| --- | --- | --- | --- |
| POST | `/api/v1/transactions` | `ingest_client` | Registrar una transacción. Devuelve `202` con `transaction_id`. Acepta `Idempotency-Key`. |
| POST | `/api/v1/transactions/batch` | `ingest_client` | Lote hasta 500. Devuelve `202` con el conteo aceptado. |
| GET | `/api/v1/transactions/{transaction_id}` | `analyst`, `admin` | Devuelve la transacción y, si existe, su `RiskAssessment`. |
| GET | `/health` | público | Liveness. |
| GET | `/ready` | público | Verifica BD y Kafka. |
| GET | `/metrics` | interno | Métricas Prometheus. |

### 3.2 scoring-service — `/api/v1/score` y `/assessments`

| Método | Ruta | Rol | Para qué |
| --- | --- | --- | --- |
| POST | `/api/v1/score/preview` | `analyst`, `admin` | Evalúa una transacción sin persistirla. Devuelve `score`, `level`, reglas activadas y top-3 SHAP. |
| GET | `/api/v1/assessments/{transaction_id}` | `analyst`, `admin` | Devuelve el `RiskAssessment` con sus `rule_hits` y `shap_factors`. |
| GET | `/api/v1/models/active` | `admin`, `analyst` | Versión y métricas del modelo activo. |
| GET | `/health`, `/ready`, `/metrics` | público/interno | Como todos. |

### 3.3 alert-service — `/api/v1/alerts`

| Método | Ruta | Rol | Para qué |
| --- | --- | --- | --- |
| GET | `/api/v1/alerts` | `analyst`, `admin` | Lista paginada con filtros `status`, `severity`, `from`, `to`. |
| GET | `/api/v1/alerts/{alert_id}` | `analyst`, `admin` | Alerta, su historial de estados y notas. |
| PATCH | `/api/v1/alerts/{alert_id}/status` | `analyst`, `admin` | Cambia estado: `IN_REVIEW`, `CONFIRMED`, `DISMISSED` (requiere `reason` fuera de `IN_REVIEW`). |
| POST | `/api/v1/alerts/{alert_id}/notes` | `analyst`, `admin` | Agrega una nota. |
| GET | `/health`, `/ready`, `/metrics` | | |

### 3.4 analytics-service — `/bi/v1`

Todas estas rutas aceptan **solo** `X-API-Key` con rol `bi_reader`.

| Método | Ruta | Para qué |
| --- | --- | --- |
| GET | `/bi/v1/kpis?from=&to=` | KPIs del periodo: transacciones, alertas, tasa, monto en riesgo, tiempo medio de resolución. |
| GET | `/bi/v1/timeseries?from=&to=&granularity=hour\|day` | Serie temporal de transacciones y alertas. |
| GET | `/bi/v1/risk-distribution?from=&to=&channel=` | Conteo por nivel de riesgo y canal. |
| GET | `/bi/v1/alerts?from=&to=&status=&page=&page_size=` | Lista paginada, sin PII. |
| GET | `/bi/v1/model-performance?model_version=` | Precisión, recall y falsos positivos. |
| GET | `/health`, `/ready` | Probes. |

### 3.5 api-gateway — rutas transversales

| Método | Ruta | Para qué |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | Login de analista/admin. |
| POST | `/api/v1/auth/refresh` | Refresca el JWT. |
| POST | `/api/v1/api-keys` | Solo `admin`: crea una API key con rol. |
| DELETE | `/api/v1/api-keys/{key_id}` | Solo `admin`: revoca una clave. |

## 4. Contratos de eventos (tópicos Kafka)

Los contratos viven en `shared-contracts/` y se versionan (sufijo `V1`). El sobre es común: `Envelope(message_id, message_type, schema_version, occurred_at, trace_id, payload)`.

| Tópico | Productor | Consumidores | Clave |
| --- | --- | --- | --- |
| `transactions.received.v1` | transaction-service | scoring, analytics | `account_id_hash` |
| `transactions.scored.v1` | scoring-service | alert, analytics | `account_id_hash` |
| `alerts.raised.v1` | alert-service | analytics, n8n (webhook) | `alert_id` |
| `alerts.resolved.v1` | alert-service | analytics | `alert_id` |
| `*.dlq` | cualquier consumidor | revisión manual | igual al original |

### 4.1 Reglas de evolución

- Añadir un campo **opcional** → misma versión.
- Cambio incompatible (renombrar, eliminar, volver obligatorio un campo) → publicar `V2` y mantener `V1` mientras los consumidores migran.
- El consumidor ignora campos desconocidos (`FAIL_ON_UNKNOWN_PROPERTIES=false`).

### 4.2 Ejemplo — `TransactionReceivedV1`

```json
{
  "message_id": "01HSZK4T...",
  "message_type": "TransactionReceived",
  "schema_version": 1,
  "occurred_at": "2026-11-12T13:45:00Z",
  "trace_id": "01HSZK2A...",
  "payload": {
    "transaction_id": "9b6c3f12-...",
    "account_id_hash": "a1b2c3...",
    "amount": 480.00,
    "currency": "PEN",
    "channel": "WEB",
    "device_id": "device-7421",
    "occurred_at": "2026-11-12T13:45:00Z"
  }
}
```

## 5. OpenAPI

Cada servicio expone su OpenAPI en `/docs` (Swagger UI) y `/openapi.json`. El gateway consolida un `/docs` general accesible por el administrador. La generación es automática desde los `Resource` de Pydantic y los `Operation` del controller, así que la fuente de verdad del contrato siempre es el código.
