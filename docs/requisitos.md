# Requisitos funcionales (RF) y no funcionales (RNF)

Basado en el one-pager y en las decisiones de arquitectura acordadas.

## 1. Requisitos funcionales (RF)

### 1.1 Ingesta y validación de transacciones

| ID | Requisito |
| --- | --- |
| RF-01 | El sistema debe aceptar transacciones individuales vía `POST /api/v1/transactions`, respondiendo `202 Accepted` apenas se publica el evento. |
| RF-02 | El sistema debe aceptar lotes de transacciones vía `POST /api/v1/transactions/batch` con un tope de 500 por lote. |
| RF-03 | El sistema debe validar que cada transacción traiga `account_id`, `amount`, `currency`, `channel`, `occurred_at` y `device_id`; una validación fallida devuelve `422` con la lista de campos. |
| RF-04 | El sistema debe soportar la cabecera `Idempotency-Key`; dos envíos con la misma clave no deben generar dos transacciones. |
| RF-05 | El sistema debe publicar el evento `TransactionReceivedV1` en Kafka al confirmar la persistencia, aplicando el patrón Outbox. |
| RF-06 | El sistema debe permitir consultar el estado y el puntaje de una transacción vía `GET /api/v1/transactions/{id}`. |

### 1.2 Scoring y explicabilidad

| ID | Requisito |
| --- | --- |
| RF-07 | El sistema debe consumir `TransactionReceivedV1` y calcular un `RiskScore` entre 0 y 100. |
| RF-08 | El puntaje debe combinar tres señales: reglas determinísticas, probabilidad de XGBoost y anomalía de Isolation Forest. |
| RF-09 | El sistema debe asignar un `RiskLevel`: bajo (0-39), medio (40-69), alto (70-89), crítico (90-100). |
| RF-10 | Cada evaluación debe guardar los tres factores SHAP con mayor impacto y las reglas activadas. |
| RF-11 | El sistema debe publicar `TransactionScoredV1` tras cada evaluación. |
| RF-12 | El sistema debe exponer `POST /api/v1/score/preview` para evaluar una transacción sin persistirla. |
| RF-13 | El sistema debe exponer `GET /api/v1/models/active` con la versión y métricas del modelo cargado. |
| RF-14 | Si el modelo falla o no carga, el sistema debe degradar a solo reglas y registrarlo. |

### 1.3 Reglas de dominio

| ID | Requisito |
| --- | --- |
| RF-15 | Las reglas de scoring deben ser configurables desde un archivo YAML, no quemadas en código. |
| RF-16 | El sistema debe soportar las reglas: velocidad, monto atípico, dispositivo nuevo, viaje imposible, horario inusual y fraccionamiento. |
| RF-17 | Al editar una regla, el sistema debe recalcular las evaluaciones futuras sin tocar las ya persistidas. |

### 1.4 Alertas y ciclo de vida

| ID | Requisito |
| --- | --- |
| RF-18 | El sistema debe crear automáticamente una `FraudAlert` cuando un `RiskScore` sea mayor o igual a 70. |
| RF-19 | Una alerta debe seguir el ciclo: `OPEN → IN_REVIEW → CONFIRMED | DISMISSED`. |
| RF-20 | El sistema no debe permitir reabrir una alerta cerrada sin registrar un motivo. |
| RF-21 | El sistema debe permitir al analista cambiar el estado vía `PATCH /api/v1/alerts/{id}/status`. |
| RF-22 | El sistema debe permitir agregar notas de investigación vía `POST /api/v1/alerts/{id}/notes`. |
| RF-23 | El sistema debe publicar `AlertRaisedV1` al crear una alerta y `AlertResolvedV1` al cerrarla. |
| RF-24 | El historial de cambios de estado debe ser append-only y auditable. |

### 1.5 Notificaciones (n8n)

| ID | Requisito |
| --- | --- |
| RF-25 | El sistema debe disparar un webhook a n8n cuando se publique `AlertRaisedV1` de nivel alto o crítico. |
| RF-26 | n8n debe enriquecer el mensaje y notificar por Telegram o por un canal configurado. |
| RF-27 | Un fallo en n8n no debe afectar la persistencia de la alerta; la notificación es un efecto secundario. |

### 1.6 Analítica y Power BI

| ID | Requisito |
| --- | --- |
| RF-28 | El sistema debe mantener un modelo de lectura alimentado por los eventos de Kafka, separado del transaccional. |
| RF-29 | El sistema debe exponer `GET /bi/v1/kpis` con transacciones, alertas, tasa de alerta y monto en riesgo del periodo. |
| RF-30 | El sistema debe exponer `GET /bi/v1/timeseries` con serie por hora o día de transacciones y alertas. |
| RF-31 | El sistema debe exponer `GET /bi/v1/risk-distribution` con conteo por nivel de riesgo y canal. |
| RF-32 | El sistema debe exponer `GET /bi/v1/alerts` paginado, sin datos personales. |
| RF-33 | El sistema debe exponer `GET /bi/v1/model-performance` con precisión, recall y falsos positivos del modelo activo. |

### 1.7 Gestión de accesos

| ID | Requisito |
| --- | --- |
| RF-34 | El sistema debe autenticar analistas y administradores con JWT de corta duración y refresh token. |
| RF-35 | El sistema debe autenticar clientes sistema (ingesta, Power BI) con API keys por rol. |
| RF-36 | El sistema debe soportar los roles: `ingest_client`, `analyst`, `admin`, `bi_reader`. |
| RF-37 | Cada rol debe estar limitado a los endpoints que le corresponden; un `bi_reader` solo accede a `/bi/v1`. |

### 1.8 Auditoría

| ID | Requisito |
| --- | --- |
| RF-38 | El sistema debe registrar en log inmutable cada cambio de estado de alerta, cambio de regla y llamada a `/bi/v1`. |
| RF-39 | El `trace_id` debe nacer en el gateway y propagarse en eventos Kafka y llamadas HTTP internas. |

## 2. Requisitos no funcionales (RNF)

### 2.1 Seguridad

| ID | Requisito |
| --- | --- |
| RNF-01 | Las API keys y credenciales deben vivir únicamente en variables de entorno, nunca en el repositorio. |
| RNF-02 | El `api-gateway` debe ser el único contenedor con puerto publicado al host; el resto queda en la red Docker privada. |
| RNF-03 | Las contraseñas de usuarios se almacenan con hashing (argon2 o bcrypt), nunca en texto plano. |
| RNF-04 | CORS se configura explícitamente, limitando orígenes a los dominios de las herramientas autorizadas. |
| RNF-05 | Cada servicio debe tener un usuario de base de datos propio con permisos solo sobre su esquema. |

### 2.2 Privacidad

| ID | Requisito |
| --- | --- |
| RNF-06 | El `account_id` debe guardarse seudonimizado (hash con sal) en las tablas y eventos. |
| RNF-07 | La API de Power BI nunca debe devolver datos que identifiquen a una persona. |
| RNF-08 | Los datos de entrenamiento del modelo se tratan como sintéticos o anonimizados. |

### 2.3 Rendimiento

| ID | Requisito |
| --- | --- |
| RNF-09 | El puntaje debe estar disponible en menos de 2 s en el percentil 95, desde la publicación del evento. |
| RNF-10 | La API de Power BI debe responder en menos de 1 s en el percentil 95 para los endpoints de KPIs. |
| RNF-11 | El sistema debe soportar al menos 100 transacciones por segundo en una sola máquina de desarrollo. |

### 2.4 Confiabilidad

| ID | Requisito |
| --- | --- |
| RNF-12 | Kafka debe entregar al menos una vez; los consumidores deben ser idempotentes y descartar duplicados. |
| RNF-13 | El Outbox pattern debe garantizar que no se pierda un evento si el servicio cae entre guardar y publicar. |
| RNF-14 | Los mensajes que fallen tres veces deben ir al tópico `.dlq` correspondiente para revisión manual. |
| RNF-15 | Si el modelo ML falla, el sistema debe degradar a solo reglas sin caerse. |

### 2.5 Observabilidad

| ID | Requisito |
| --- | --- |
| RNF-16 | Todos los servicios deben emitir logs estructurados en JSON con `trace_id`, servicio y operación. |
| RNF-17 | Todos los servicios deben exponer `/health` (liveness) y `/ready` (verifica BD y Kafka). |
| RNF-18 | Todos los servicios deben exponer métricas Prometheus en `/metrics`. |

### 2.6 Mantenibilidad

| ID | Requisito |
| --- | --- |
| RNF-19 | El código debe organizarse por microservicios con arquitectura hexagonal + DDD. |
| RNF-20 | Ningún servicio debe importar código de otro servicio; solo se comparte `shared-contracts`. |
| RNF-21 | Los contratos de eventos deben versionarse y validarse con modelos Pydantic. |
| RNF-22 | La capa `domain` no debe importar FastAPI, SQLAlchemy ni la librería de Kafka. |
| RNF-23 | Cada servicio debe tener pruebas unitarias del dominio, integración con Testcontainers y contrato con `shared-contracts`. |

### 2.7 Portabilidad

| ID | Requisito |
| --- | --- |
| RNF-24 | Todo el sistema debe levantar con `docker compose up` en cualquier máquina con Docker. |
| RNF-25 | Debe ser posible reemplazar Kafka por RabbitMQ u otro broker tocando solo adaptador y configuración, sin cambiar el dominio ni la aplicación. |
| RNF-26 | Un servicio debe poder migrar su stack (por ejemplo, Python → Java) sin afectar a los demás, siempre que respete los contratos de eventos. |

### 2.8 Escalabilidad

| ID | Requisito |
| --- | --- |
| RNF-27 | Cada servicio debe poder escalarse horizontalmente agregando réplicas sin cambios en el código. |
| RNF-28 | Las claves de partición Kafka deben ser `account_id` para preservar orden por cuenta y repartir carga. |

### 2.9 Calidad (cobertura ISO/IEC 25010)

| Característica | Cómo la cubre FraudShield |
| --- | --- |
| Adecuación funcional | Reglas y modelo validados contra datos etiquetados, con métricas medidas (PR-AUC) |
| Eficiencia de desempeño | Procesamiento asíncrono con Kafka, índices por `account_id`, caché en `/bi/v1` |
| Compatibilidad | Contratos de eventos y API versionados (`V1`, `/v1`) |
| Fiabilidad | Reintentos, DLQ, Outbox, idempotencia, degradación a solo reglas |
| Seguridad | Autenticación, roles, red privada, seudonimización, auditoría |
| Mantenibilidad | Microservicios, DDD, hexagonal, pruebas, CI |
| Portabilidad | Docker Compose; adaptadores intercambiables (broker, modelo) |
| Usabilidad | Documentación OpenAPI generada por FastAPI; Power BI con reporte de 4 páginas |
