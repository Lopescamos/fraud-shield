# Épicas, priorización y estimación

## 1. Épicas

| # | Épica | Resumen |
| --- | --- | --- |
| E1 | Ingesta y publicación de transacciones | API REST que recibe transacciones (individuales y en lote), las valida, aplica idempotencia y las publica en Kafka mediante Outbox. |
| E2 | Scoring determinístico y explicable | Motor de reglas configurable por YAML + modelos XGBoost e Isolation Forest + explicación SHAP por evaluación. |
| E3 | Alertas y ciclo de vida | Creación automática de `FraudAlert`, estados auditables (`OPEN → IN_REVIEW → CONFIRMED | DISMISSED`), notas y motivos. |
| E4 | Notificaciones por n8n | Webhook saliente hacia n8n para alertas altas o críticas; enriquecimiento y envío por Telegram o canal configurado. |
| E5 | API de analítica para Power BI | Endpoints de solo lectura `/bi/v1`, paginados y autenticados por API key, que alimentan el reporte. |
| E6 | Gestión de accesos | JWT para analistas y administradores; API keys por rol (`ingest_client`, `analyst`, `admin`, `bi_reader`); CORS controlado. |
| E7 | Mensajería confiable | Contratos versionados, consumidores idempotentes, reintentos con backoff, DLQ y Outbox pattern. |
| E8 | Observabilidad y operación | Logs JSON con `trace_id`, probes `/health` y `/ready`, métricas Prometheus, tablero de salud opcional. |
| E9 | CI/CD y empaquetado | Pipeline GitHub Actions con lint, tipos, pruebas unitarias, integración con Testcontainers, contratos, imágenes Docker y despliegue a GHCR. |
| E10 | Dataset y simulador de tráfico | Generador propio (`traffic-simulator`) que emite transacciones normales y escenarios de fraude conocidos usando la API como cliente. |

Ver `user-stories.md` para el detalle de cada épica con criterios de aceptación.

## 2. Priorización del MVP (MoSCoW)

| Prioridad | Épicas / elementos |
| --- | --- |
| Must | E1 (ingesta), E2 (scoring con reglas + un modelo), E3 (alertas básicas), E7 (idempotencia + Outbox), E8 (observabilidad mínima) |
| Should | E6 (accesos completos), E5 (API Power BI con KPIs y timeseries), E10 (simulador de tráfico) |
| Could | E4 (n8n), E2 extendido con SHAP y Isolation Forest, E5 completo con 5 endpoints, E9 (pipeline con despliegue a GHCR) |
| Won't (por ahora) | Entrenamiento continuo del modelo, panel propio de analista, integración con sistema de bloqueo, alta disponibilidad multi-región, migración de un servicio a Java |

## 3. Estimación rápida (tallas S / M / L)

| Épica | Talla | Nota |
| --- | --- | --- |
| E1 — Ingesta y publicación | M | API REST, validación, idempotencia y Outbox; grande por la cantidad de piezas que integra. |
| E2 — Scoring | L | Reglas + dos modelos + SHAP + versionado del modelo; la épica más grande. |
| E3 — Alertas | M | Ciclo de estados, notas, motivos y auditoría; lógica sencilla pero con muchos endpoints. |
| E4 — Notificaciones n8n | S | Webhook saliente, flujo n8n exportado; depende más de configuración que de código. |
| E5 — API Power BI | M | Modelo de lectura + 5 endpoints paginados + caché + reporte de 4 páginas. |
| E6 — Accesos | M | JWT + refresh + API keys + roles + CORS; lógica estándar pero con varios casos. |
| E7 — Mensajería confiable | L | Contratos, consumidores idempotentes, reintentos, DLQ y Outbox; atraviesa todos los servicios. |
| E8 — Observabilidad | S | Logs, probes, métricas; se agrega una sola vez al inicio y se mantiene. |
| E9 — CI/CD | M | Pipeline con varias etapas; se arma en Sprint 0 y se extiende durante el proyecto. |
| E10 — Simulador de tráfico | S | Script con Faker que consume la API como cualquier cliente. |

La talla es una señal de tamaño relativo para planear sprints, no una estimación en horas. Las más grandes (E2 y E7) conviene partirlas en historias chicas antes de meterlas a un sprint.
