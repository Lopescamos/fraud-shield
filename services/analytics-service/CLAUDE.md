# analytics-service — CLAUDE.md

## 1. Rol en el sistema
Bounded context de **Analítica**. Es la cara de **lectura** del sistema (CQRS read-side): consume los cuatro eventos de integración y los proyecta en tablas desnormalizadas pensadas para Power BI. Expone una API REST de solo lectura, protegida por API key.

## 2. Diferencia deliberada con los otros servicios
Este servicio **no sigue DDD con agregados ricos** como `transaction-service`, `scoring-service` o `alert-service`. No tiene reglas de negocio propias: solo proyecta y consulta. Por eso:

- `domain/` contiene **vistas** (`TransactionView`, `AlertView`) sin comportamiento, más los VOs reutilizados (`RiskScore`, `Decision`, `AlertStatus`, `Priority`) y dos puertos (`AnalyticsReadRepository` para lectura, `AnalyticsProjectionRepository` para escritura idempotente).
- `kernel/` es reducido: `Result`, `Ids`, `IdempotentExecutor`. **No hay `AbstractDomainAggregateRoot`** porque este servicio no emite eventos de dominio propios.
- No hay patrón **Outbox** porque este servicio no publica eventos: es un consumidor terminal.

## 3. Lenguaje
- **TransactionView**: proyección combinada de `TransactionReceivedV1` + `TransactionScoredV1` sobre la misma `transaction_id`.
- **AlertView**: proyección combinada de `AlertRaisedV1` + `AlertResolvedV1` sobre el mismo `alert_id`.
- **daily_metrics**: tabla de métricas diarias (volumen, tasa de fraude, distribución por prioridad). Se calcula **on-the-fly** con queries agregadas sobre las vistas; no se materializa ni requiere jobs.
- **Processed events**: `analytics.processed_events` (PK compuesta `message_id, consumer_group`) para idempotencia por `message_id`.

## 4. Mensajes
### Consume (todos deshabilitados por `ANALYTICS_CONSUMER_ENABLED=false`)
- `TransactionReceivedV1` (topic `transactions.received.v1`, grupo `analytics.ingest-received`)
- `TransactionScoredV1` (topic `transactions.scored.v1`, grupo `analytics.ingest-scored`)
- `AlertRaisedV1` (topic `alerts.raised.v1`, grupo `analytics.ingest-alerts`)
- `AlertResolvedV1` (topic `alerts.resolved.v1`, grupo `analytics.ingest-alerts`)
### Publica
- (ninguno) — consumidor terminal, no hay outbox.

## 5. Endpoints (todos requieren `X-API-Key`)
- `GET /analytics/transactions` — filtros `from`, `to`, `decision`, `country`, `limit`, `offset`.
- `GET /analytics/alerts` — filtros `status`, `priority`, `limit`, `offset`.
- `GET /analytics/metrics/daily` — rango de fechas, agrupado por día.
- `GET /analytics/metrics/summary` — totales acumulados.
- `GET /health`, `GET /ready` — probes (sin API key).

## 6. Autenticación
- Header `X-API-Key`. Las claves válidas se cargan desde `ANALYTICS_API_KEYS` (CSV).
- Falta/clave inválida → **401** Problem Details.
- `/health` y `/ready` quedan exentos.
- Power BI usa el conector **Web**/JSON con esta key.

## 7. Reglas específicas
- Cada proyección es idempotente por `(message_id, consumer_group)` via `IdempotentExecutor`.
- Todos los `UPSERT` son en la misma transacción que el marker `processed_events`.
- Los contratos de entrada son **data**: tolerar campos nuevos (`extra="ignore"` ya viene en `shared_contracts`).

## 8. Referencias
- Historias: US-12 (Power BI via analytics API), US-13 (métricas diarias), US-14 (filtros para el analista BI).
- ADRs: ADR-008 (Power BI via API), ADR-004 (postgres por servicio).
