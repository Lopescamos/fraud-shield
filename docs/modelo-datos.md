# Modelo de datos

Una sola instancia de PostgreSQL con **un esquema por microservicio** y **un usuario de base de datos por servicio**, con permisos solo sobre su esquema. Es la forma recomendada en la guía de arquitectura: mantiene el aislamiento lógico sin levantar cuatro motores. Los esquemas se crean desde `infra/database/postgres/init.sql` y las migraciones viven **dentro de cada servicio** (Alembic), nunca en la raíz.

El código fuente del diagrama está en `fraudshield-erd.puml`.

> Convenciones generales: todas las tablas en **snake_case y plural**; claves primarias `id BIGSERIAL`; identificadores de negocio como `UUID`; timestamps `TIMESTAMPTZ` con `created_at` y `updated_at`; montos como `NUMERIC(14,2)`; auditoría append-only.

---

## 1. Esquema `tx` — transaction-service

Responsable de recibir, persistir y publicar transacciones.

### 1.1 `transactions`

Hecho central del servicio. Particionada por mes (`occurred_at`) para consultas de ventana.

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | BIGSERIAL PK | Clave técnica. |
| `transaction_id` | UUID UNIQUE | Generado por el dominio. |
| `account_id_hash` | VARCHAR(64) | Seudonimizado (hash + sal). |
| `amount` | NUMERIC(14,2) | Monto. |
| `currency` | CHAR(3) | ISO 4217. |
| `channel` | VARCHAR(16) | `WEB`, `MOBILE`, `POS`. |
| `device_id` | VARCHAR(64) | Dispositivo observado. |
| `geo_lat`, `geo_lng` | NUMERIC(9,6) | Opcional. |
| `occurred_at` | TIMESTAMPTZ | Hora en origen. |
| `received_at` | TIMESTAMPTZ | Hora en el servicio. |
| `created_at`, `updated_at` | TIMESTAMPTZ | Auditoría. |

**Índices:** `(account_id_hash, occurred_at DESC)` para las reglas de velocidad; `(occurred_at)` para particionado.

### 1.2 `accounts_profile`

Perfil mínimo de la cuenta para alimentar reglas (promedio de monto, dispositivos conocidos). Lo mantiene el servicio con los propios eventos que recibe.

### 1.3 `outbox_events`

Patrón Outbox: cada transacción escribe aquí el evento a publicar, en la misma transacción.

| Columna | Tipo |
| --- | --- |
| `id` | BIGSERIAL PK |
| `message_id` | UUID UNIQUE |
| `channel` | VARCHAR(80) — ej. `transactions.received.v1` |
| `message_key` | VARCHAR(64) — `account_id_hash` |
| `message_type` | VARCHAR(80) |
| `schema_version` | SMALLINT |
| `payload` | JSONB |
| `status` | VARCHAR(16) — `PENDING | PUBLISHED | FAILED` |
| `attempts` | SMALLINT |
| `published_at` | TIMESTAMPTZ |
| `created_at` | TIMESTAMPTZ |

**Índice:** `(status, created_at)` para que el relay seleccione pendientes con `FOR UPDATE SKIP LOCKED`.

### 1.4 `idempotency_keys`

Soporta la cabecera HTTP `Idempotency-Key`: un reenvío devuelve la misma `transaction_id`.

---

## 2. Esquema `scoring` — scoring-service

Responsable de evaluar el riesgo de cada transacción.

### 2.1 `risk_assessments`

Hecho central del servicio.

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | BIGSERIAL PK | |
| `assessment_id` | UUID UNIQUE | Generado por el dominio. |
| `transaction_id` | UUID UNIQUE | Puntaje único por transacción. |
| `account_id_hash` | VARCHAR(64) | |
| `score` | SMALLINT | 0–100. |
| `level` | VARCHAR(10) | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`. |
| `rules_score` | SMALLINT | Aporte de reglas. |
| `xgb_probability` | NUMERIC(4,3) | Probabilidad XGBoost. |
| `iforest_anomaly` | NUMERIC(4,3) | Anomalía normalizada. |
| `degraded_mode` | BOOLEAN | `true` si se evaluó solo con reglas. |
| `model_version` | VARCHAR(40) | FK lógica a `model_registry.version`. |
| `created_at` | TIMESTAMPTZ | |

**Índices:** `(transaction_id)` único, `(level, created_at)` para listados.

### 2.2 `rule_hits`

Una fila por regla activada. `(assessment_id, rule_code)` único.

### 2.3 `shap_factors`

Los tres factores SHAP con mayor impacto por evaluación. `rank` 1–3; `feature`, `shap_value`, `direction`.

### 2.4 `model_registry`

Historial de modelos entrenados (`version`, `algorithm`, `precision`, `recall`, `pr_auc`, `trained_at`, `is_active`). Un solo `is_active=true`.

### 2.5 `processed_events`

Idempotencia del consumidor: `(message_id, consumer_group)` único. Se escribe en la misma transacción que el `risk_assessment`.

---

## 3. Esquema `alerts` — alert-service

Responsable del ciclo de vida de las alertas.

### 3.1 `fraud_alerts`

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | BIGSERIAL PK | |
| `alert_id` | UUID UNIQUE | Generado por el dominio. |
| `transaction_id` | UUID | Transacción origen. |
| `account_id_hash` | VARCHAR(64) | |
| `severity` | VARCHAR(10) | `HIGH`, `CRITICAL`. |
| `status` | VARCHAR(16) | `OPEN`, `IN_REVIEW`, `CONFIRMED`, `DISMISSED`. |
| `analyst_id` | UUID | Nullable hasta la toma. |
| `opened_at` | TIMESTAMPTZ | |
| `closed_at` | TIMESTAMPTZ | Nullable. |

**Índices:** `(status, severity, opened_at)` para la bandeja; `(transaction_id)` único.

### 3.2 `alert_notes`

Notas de investigación: `alert_id`, `author`, `body`, `created_at`.

### 3.3 `alert_status_history`

Append-only. `alert_id`, `from_status`, `to_status`, `changed_by`, `reason`, `changed_at`.

### 3.4 `outbox_events` y `processed_events`

Mismo formato que en `tx` y `scoring`.

---

## 4. Esquema `analytics` — analytics-service

Modelo de lectura en estrella, alimentado por los eventos. **Nunca** se escribe desde fuera del servicio.

### 4.1 Tablas de hechos

- `fact_transactions` — una fila por transacción observada: `transaction_id`, `account_id_hash`, `amount`, `currency`, `channel_id` (FK), `date_id` (FK), `occurred_at`.
- `fact_alerts` — una fila por alerta: `alert_id`, `transaction_id`, `severity`, `status`, `risk_level_id` (FK), `date_opened_id` (FK), `date_closed_id` (FK), `resolution_minutes`.

### 4.2 Tablas de dimensión

- `dim_date` — `date_id`, `year`, `quarter`, `month`, `day`, `hour`, `day_of_week`.
- `dim_channel` — `channel_id`, `name`, `description`.
- `dim_risk_level` — `risk_level_id`, `code`, `name`, `min_score`, `max_score`.

### 4.3 Vistas materializadas

- `vw_kpi_daily` — totales por día: transacciones, alertas, monto en riesgo, tiempo medio de resolución.
- `vw_alert_funnel` — conteo por estado en el periodo.
- `vw_model_performance` — métricas vigentes del modelo activo.

---

## 5. Aislamiento y permisos

Desde `infra/database/postgres/init.sql`:

```sql
CREATE SCHEMA tx;
CREATE SCHEMA scoring;
CREATE SCHEMA alerts;
CREATE SCHEMA analytics;

CREATE USER tx_user       WITH PASSWORD 'dev_tx';
CREATE USER scoring_user  WITH PASSWORD 'dev_scoring';
CREATE USER alerts_user   WITH PASSWORD 'dev_alerts';
CREATE USER analytics_user WITH PASSWORD 'dev_analytics';

GRANT USAGE, CREATE ON SCHEMA tx        TO tx_user;
GRANT USAGE, CREATE ON SCHEMA scoring   TO scoring_user;
GRANT USAGE, CREATE ON SCHEMA alerts    TO alerts_user;
GRANT USAGE, CREATE ON SCHEMA analytics TO analytics_user;

ALTER ROLE tx_user        SET search_path = tx;
ALTER ROLE scoring_user   SET search_path = scoring;
ALTER ROLE alerts_user    SET search_path = alerts;
ALTER ROLE analytics_user SET search_path = analytics;
```

Cada usuario solo ve su esquema. Las contraseñas del bloque anterior son para desarrollo local; en cualquier otro entorno llegan por variables de entorno.

---

## 6. Migraciones

- Alembic por servicio, en `services/<servicio>/migrations/`.
- `env.py` apunta al `search_path` de su esquema.
- `alembic.ini` por servicio, con `sqlalchemy.url` leído de `DATABASE_URL`.
- Numeración `V1__descripcion.sql` para que el orden sea evidente.
- Ningún servicio migra tablas de otro esquema.

---

## 7. Qué **no** está aquí

- Las credenciales reales (viven en `infra/.env`).
- El esquema de n8n: usa su propia base; no comparte PostgreSQL con los servicios.
- Datos de entrenamiento del modelo: viven en `data/` (ignorado por git).
