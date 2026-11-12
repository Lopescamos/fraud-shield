# Arquitectura — modelo C4

Este documento describe el sistema en los tres niveles C4 que mejor se aplican al proyecto: **Contexto (C1)**, **Contenedores (C2)** y **Componentes (C3)**. El código fuente de los diagramas está en `fraudshield-structurizr.dsl`; este archivo da el "qué" y el "por qué" en prosa, y los diagramas dan el "cómo se ve".

> Convenio de términos: **servicio** = contenedor desplegable (microservicio); **componente** = módulo interno de un servicio (capa DDD). El broker es Apache Kafka, pero se considera un detalle de infraestructura detrás del puerto `MessagePublisher`.

---

## 1. Nivel 1 — Contexto (C1)

Qué sistemas y personas interactúan con FraudShield y para qué.

### Actores

| Actor | Rol |
| --- | --- |
| Sistema de ingesta (banco/fintech) | Envía transacciones por API para evaluación de riesgo. |
| Analista de fraude | Revisa alertas, cambia su estado y deja notas. |
| Administrador de riesgo | Gestiona reglas, modelos y usuarios. |
| Analista de negocio (Power BI) | Consume KPIs y reportes operativos. |

### Sistemas externos

| Sistema | Rol |
| --- | --- |
| Apache Kafka | Broker de eventos (parte interna de FraudShield, pero intercambiable). |
| n8n | Orquestador de notificaciones ante alertas altas o críticas. |
| Telegram / Outlook (vía Power Automate) | Canal de notificación al que n8n envía. |
| Power BI Desktop | Consume la API `/bi/v1` para su reporte. |

### Vista en prosa

Un cliente envía transacciones al `api-gateway`. FraudShield las evalúa internamente, genera alertas cuando el riesgo es alto o crítico, notifica por n8n y expone métricas por una API separada que Power BI consume. La base de datos **nunca** se expone al exterior.

---

## 2. Nivel 2 — Contenedores (C2)

Qué piezas desplegables hay y cómo se comunican.

### Contenedores

| Contenedor | Tecnología | Puerto publicado | Responsabilidad |
| --- | --- | --- | --- |
| api-gateway | FastAPI + Python 3.12 | 8000 | Autenticación, rate limiting, enrutamiento. Único con puerto publicado al host. |
| transaction-service | FastAPI + Python 3.12 | interno (8001) | Recibe transacciones, aplica idempotencia, persiste y publica `TransactionReceivedV1`. |
| scoring-service | FastAPI + Python 3.12 | interno (8002) | Consume `TransactionReceivedV1`, calcula el puntaje y publica `TransactionScoredV1`. |
| alert-service | FastAPI + Python 3.12 | interno (8003) | Consume `TransactionScoredV1`, crea alertas y expone su ciclo de vida. |
| analytics-service | FastAPI + Python 3.12 | interno (8004) | Mantiene un modelo de lectura en estrella y expone `/bi/v1`. |
| postgres | PostgreSQL 16 | interno (5432) | Base relacional única con un esquema y un usuario por servicio. |
| kafka | Apache Kafka KRaft | interno (9092) | Log de eventos; tópicos versionados y con DLQ. |
| n8n | n8n (contenedor oficial) | 5678 (solo demo) | Flujo de notificación disparado por webhook. |
| traffic-simulator | Python + Faker | sin puerto | Perfil `demo`: emite tráfico sintético usando la API como cliente. |

### Comunicación entre contenedores

| Origen → destino | Protocolo | Para qué |
| --- | --- | --- |
| cliente externo → api-gateway | HTTPS + JWT / API key | Entrada única al sistema. |
| api-gateway → cada servicio | HTTP interno | Enrutamiento tras autenticar y autorizar. |
| transaction-service → kafka | AIOKafka (TCP) | Publica `TransactionReceivedV1` desde el Outbox. |
| scoring-service → kafka | AIOKafka | Consume y publica `TransactionScoredV1`. |
| alert-service → kafka | AIOKafka | Consume y publica `AlertRaisedV1`, `AlertResolvedV1`. |
| analytics-service → kafka | AIOKafka | Consume para alimentar su modelo de lectura. |
| alert-service → n8n | HTTPS webhook | Dispara notificación en alertas altas/críticas. |
| cada servicio → postgres | asyncpg | Lee y escribe únicamente su esquema. |
| Power BI → api-gateway → analytics-service | HTTPS + API key | Lee endpoints `/bi/v1`. |

### Vista en prosa

El sistema es un conjunto de servicios FastAPI que se comunican casi siempre por eventos de Kafka. La única comunicación síncrona cliente-a-sistema pasa por el `api-gateway`. Cada servicio es dueño de su esquema en PostgreSQL y no lee tablas ajenas; si necesita datos de otro contexto, lo obtiene por evento y mantiene su propia copia (modelo de lectura).

---

## 3. Nivel 3 — Componentes (C3)

Cada servicio sigue arquitectura hexagonal + DDD con cuatro capas y un `kernel`. Esta vista aplica dentro de cada microservicio.

### 3.1 transaction-service

| Componente | Capa | Qué hace |
| --- | --- | --- |
| `Transaction` (aggregate) | domain | Representa la transacción recibida; inmutable una vez registrada. |
| `AccountId`, `Money`, `Channel`, `DeviceId` | domain/valueobjects | Reglas de tipo y rango. |
| `RegisterTransactionCommand`, `GetTransactionByIdQuery` | domain | Entrada al servicio. |
| `TransactionRepository` (puerto) | domain | Contrato de persistencia. |
| `TransactionCommandService` | application | Caso de uso `register`; aplica idempotencia y Outbox. |
| `TransactionQueryService` | application | Consultas simples por `id`. |
| `MessagePublisher` (puerto) + `OutboxMessagePublisher` | application + infrastructure | Publicación mediante Outbox. |
| `TransactionsController`, `TransactionAcceptedResource` | interfaces/rest | Endpoint `POST /api/v1/transactions`. |
| `AccountProfilePersistenceEntity` | infrastructure | Perfil minimal para reglas de velocidad. |

### 3.2 scoring-service

| Componente | Capa | Qué hace |
| --- | --- | --- |
| `RiskAssessment` (aggregate) | domain | Resultado de evaluar una transacción. |
| `RiskScore`, `RiskLevel`, `Explanation`, `RuleHit` | domain/valueobjects | Rango, niveles y detalle. |
| `AssessTransactionCommand` | domain | Entrada al servicio. |
| `RiskModel`, `Explainer`, `RuleCatalog` (puertos) | domain/services | Capacidades centrales del negocio; adaptadores en `infrastructure`. |
| `XGBoostRiskModel`, `IsolationForestRiskModel`, `ShapExplainer`, `YamlRuleCatalog` | infrastructure | Implementaciones concretas. |
| `AssessmentCommandService` | application | Combina reglas + modelos + explicación. |
| `TransactionRegisteredConsumer`, `AssessTransactionCommandFromEventAssembler` | interfaces/messaging | Pareja del consumer y su ACL. |
| `ScoringController`, `ScorePreviewResource` | interfaces/rest | Endpoints `/score/preview`, `/assessments/{id}`, `/models/active`. |

### 3.3 alert-service

| Componente | Capa | Qué hace |
| --- | --- | --- |
| `FraudAlert` (aggregate) | domain | Alerta y su ciclo de vida. |
| `AlertStatus`, `Severity`, `AnalystId`, `AlertNote` | domain/valueobjects | Estados y datos asociados. |
| `RaiseAlertCommand`, `ChangeAlertStatusCommand`, `AddAlertNoteCommand` | domain | Entradas al servicio. |
| `AlertRepository` (puerto) | domain | Contrato de persistencia. |
| `AlertCommandService`, `AlertQueryService` | application | Casos de uso y consultas. |
| `NotificationSender` (puerto) + `N8nWebhookSender` | application + infrastructure | Notificación a n8n. |
| `TransactionScoredConsumer` | interfaces/messaging | Dispara la creación de alertas. |
| `AlertsController` | interfaces/rest | `GET /alerts`, `PATCH /alerts/{id}/status`, `POST /alerts/{id}/notes`. |

### 3.4 analytics-service

Servicio de solo lectura: no tiene commands ni `CommandService`. Mantiene un modelo de lectura (esquema en estrella) alimentado por los tres tópicos y expone `/bi/v1`.

| Componente | Capa | Qué hace |
| --- | --- | --- |
| `FactTransaction`, `FactAlert`, `DimDate`, `DimChannel`, `DimRiskLevel` | domain (modelo de lectura) | Entidades del modelo en estrella. |
| `KpiQuery`, `TimeseriesQuery`, `RiskDistributionQuery`, `AlertsQuery`, `ModelPerformanceQuery` | domain | Consultas del negocio. |
| `AnalyticsQueryService` | application | Implementa las consultas. |
| `TransactionReceivedConsumer`, `TransactionScoredConsumer`, `AlertRaisedConsumer` | interfaces/messaging | Mantienen el modelo de lectura al día. |
| `BiController` | interfaces/rest | Endpoints `/bi/v1/kpis`, `/timeseries`, `/risk-distribution`, `/alerts`, `/model-performance`. |

### 3.5 api-gateway

No es un BC con DDD; es infraestructura de entrada.

| Componente | Qué hace |
| --- | --- |
| `AuthMiddleware` | Valida JWT o API key y resuelve el rol. |
| `RateLimiter` | Límite por clave y por IP. |
| `Router` | Mapea rutas públicas a servicios internos. |
| `AuditLogger` | Registra cada llamada autenticada con `trace_id`. |

---

## 4. Vista de despliegue (bonus)

Todo el sistema levanta con `docker compose up`. La única forma de contactar un servicio desde fuera de Docker es a través del `api-gateway`.

- **Red privada:** `fraudshield-net` (bridge). Contiene `postgres`, `kafka`, los cuatro servicios y el gateway.
- **Volúmenes:** `pgdata` (Postgres), `kafka-data` (log de Kafka).
- **Puertos publicados al host:** `8000` (gateway), `5678` (n8n solo en perfil demo), `8080` (kafka-ui solo en perfil `observability`).
- **Perfiles:** `core` (servicios), `demo` (traffic-simulator), `observability` (Prometheus + Grafana).

---

## 5. Decisiones de arquitectura

Las decisiones están en `adr/` (un archivo por decisión). Las principales:

- ADR-001 — Monorepo por producto.
- ADR-002 — Apache Kafka como broker, tras `MessagePublisher`.
- ADR-003 — Python + FastAPI como stack base.
- ADR-004 — PostgreSQL con un esquema por servicio.
- ADR-005 — ID generado por el dominio (UUID), no por la base de datos.
- ADR-006 — Outbox pattern + idempotencia por `message_id`.
- ADR-007 — Reglas + XGBoost + Isolation Forest + SHAP.
- ADR-008 — Power BI consume una API dedicada, no la base de datos.
- ADR-009 — Microservicios en vez de monolito modular.
