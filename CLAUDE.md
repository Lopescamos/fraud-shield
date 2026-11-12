# CLAUDE.md — FraudShield

Reglas globales del monorepo para Claude Code. Este archivo vive en la raíz y aplica a todos los servicios. Cada servicio tiene además su propio `CLAUDE.md` con su lenguaje ubicuo, agregados y mensajes.

Autor: Kevin Edu Lopez Montalvo (U20241D958) · Lima, Perú.

---

## 1. Qué es este proyecto

**FraudShield** es una plataforma de detección de fraude transaccional basada en eventos. Recibe transacciones por API, las publica en Kafka, calcula un puntaje de riesgo explicable (reglas + ML + SHAP), genera alertas y expone métricas a Power BI mediante una API dedicada.

Si vas a programar o responder una pregunta sobre el proyecto, lee primero el documento que corresponda; nunca contestes de memoria si la respuesta vive en un `.md`.

### Documentos de referencia

| Tema | Documento |
| --- | --- |
| Visión general, alcance, usuarios | `docs/one-pager.md` |
| Qué hace el sistema (RF y RNF) | `docs/requisitos.md` |
| Épicas, MoSCoW, tallas | `docs/epicas.md` |
| Historias de usuario con criterios | `docs/user-stories.md` |
| Arquitectura C4 (contexto, contenedores, componentes) | `docs/arquitectura-c4.md` |
| Diagrama C4 (código fuente) | `docs/fraudshield-structurizr.dsl` |
| Modelo de datos y esquemas | `docs/modelo-datos.md` |
| ERD (código fuente) | `docs/fraudshield-erd.puml` |
| Contrato de API y convenciones | `docs/contrato-api.md` |
| Decisiones de arquitectura | `docs/adr/ADR-NNN-*.md` |

---

## 2. Stack y convenciones generales

- **Lenguaje:** Python 3.12 en todos los servicios.
- **Gestor de dependencias:** Poetry 2.x, un `pyproject.toml` y un `.venv/` por servicio.
- **Framework HTTP:** FastAPI + Pydantic v2.
- **Persistencia:** SQLAlchemy 2 async + asyncpg + Alembic. PostgreSQL 16, un esquema y un usuario por servicio.
- **Mensajería:** Apache Kafka (KRaft) tras el puerto `MessagePublisher`. Patrón Outbox + idempotencia por `message_id`.
- **ML:** XGBoost, scikit-learn (Isolation Forest), SHAP.
- **Calidad:** ruff (lint + format), mypy, pytest, pytest-asyncio, testcontainers, import-linter.

### Nomenclatura

| Qué | Convención | Ejemplo |
| --- | --- | --- |
| Repositorio y carpeta raíz | una palabra, minúscula | `fraudshield` |
| Carpeta del servicio | kebab-case con sufijo `-service` | `transaction-service` |
| Paquete Python en `src/` | minúscula; sin guiones medios; `snake_case` con dos palabras | `transaction`, `api_gateway` |
| Clases | PascalCase | `RiskAssessment` |
| Funciones y variables | snake_case | `register_transaction` |
| Constantes / env vars | MAYÚSCULAS con guion bajo | `DATABASE_URL` |
| Tablas | plural, snake_case | `risk_assessments` |
| URLs | minúscula, plural, versionadas | `/api/v1/transactions` |
| Canales Kafka | `contexto.aggregate.evento` + versión | `transactions.received.v1` |
| Eventos | nombre en pasado + versión | `TransactionReceivedV1` |
| Commands | imperativo | `RegisterTransactionCommand` |

### Estructura del monorepo

```
fraudshield/
├── CLAUDE.md                       ← este archivo
├── .claude/
│   ├── agents/                     ← agentes por capa (ver §4)
│   ├── commands/                   ← slash commands (ver §5)
│   └── settings.json               ← permisos compartidos
├── docs/                           ← documentación del proyecto (§1)
├── state/                          ← estado vivo por servicio
├── infra/                          ← docker-compose, init.sql, kafka, n8n
├── services/
│   ├── api-gateway/
│   ├── transaction-service/
│   ├── scoring-service/
│   ├── alert-service/
│   └── analytics-service/
├── shared-contracts/               ← eventos Pydantic versionados
├── powerbi/                        ← reporte .pbix
├── .github/workflows/ci.yml
└── README.md
```

Cada servicio sigue la misma forma interna:

```
services/<servicio>/
├── CLAUDE.md
├── pyproject.toml
├── alembic.ini
├── migrations/
├── src/<paquete>/
│   ├── main.py
│   ├── kernel/
│   ├── domain/{model,repositories,services}/
│   ├── application/{commandservices,queryservices,internal/{eventhandlers,outboundservices}}/
│   ├── infrastructure/{persistence,messaging/outbox,config}/
│   └── interfaces/{rest/{resources,transform},messaging/{consumers,transform}}/
└── tests/{unit,integration,contract}/
```

---

## 3. Reglas que siempre aplican

1. **La capa `domain` no importa FastAPI, SQLAlchemy ni Kafka.** Los puertos van en `domain/repositories` o `domain/services`; los adaptadores viven en `infrastructure`.
2. **Ningún servicio importa código de otro servicio.** El único paquete compartido es `shared-contracts`.
3. **Todo command service devuelve `Result[T, ApplicationError]`,** no lanza excepciones al exterior; es `@transactional` sobre la sesión async.
4. **Toda publicación pasa por el Outbox.** `application` escribe el evento en la tabla `outbox_events`; el relay lo publica a Kafka.
5. **Todo consumidor es idempotente.** Usa `IdempotentExecutor` y, además, respalda con `UNIQUE` donde aplique.
6. **Los contratos `shared-contracts` son solo datos** (modelos Pydantic + `Envelope`). Cambios compatibles usan la misma versión; cambios incompatibles crean `V2`.
7. **Un servicio es dueño de su esquema de base.** No se lee ni escribe el esquema de otro servicio.
8. **Los ID de negocio son UUID generados por el dominio**, no autoincrementales.
9. **Nunca pongas secretos en el repo.** Van en `infra/.env`, ignorado por git. Se versiona `infra/.env.example`.
10. **No crees carpetas que el servicio no necesite.** Si un servicio no consume mensajes (p. ej. `transaction-service` al inicio), omite `interfaces/messaging/`.

---

## 4. Agentes por capa — `.claude/agents/`

Cuando se te invoque un agente por nombre (o cuando decidas usarlo), cárgalo y sigue sus instrucciones. El agente conoce **su capa**; para otra capa delega al agente que corresponde.

| Agente | Archivo | Para qué se usa | Lee |
| --- | --- | --- | --- |
| `domain` | `.claude/agents/domain.md` | Aggregates, value objects, commands, queries, eventos de dominio, puertos. Código Python puro, sin dependencias externas. | `docs/arquitectura-c4.md`, `docs/modelo-datos.md`, `CLAUDE.md` del servicio |
| `application` | `.claude/agents/application.md` | Command/query services, event handlers, puertos `MessagePublisher` y `outboundservices/`. Devuelve `Result`. | Lo del agente domain + `docs/user-stories.md` |
| `infrastructure` | `.claude/agents/infrastructure.md` | SQLAlchemy async, Alembic, Outbox, adaptadores de broker, clientes HTTP a otros servicios o APIs externas. | `docs/modelo-datos.md`, `docs/adr/ADR-002-kafka-broker.md`, `docs/adr/ADR-004-postgresql-por-servicio.md`, `docs/adr/ADR-006-outbox-idempotencia.md` |
| `interfaces` | `.claude/agents/interfaces.md` | Controllers FastAPI, Resources (Pydantic), Transform assemblers, consumidores Kafka. Traducen a commands. | `docs/contrato-api.md` |
| `tests` | `.claude/agents/tests.md` | Unit del dominio, integración con Testcontainers, contratos contra `shared-contracts`, ArchUnit-equivalent con `import-linter`. | `docs/requisitos.md`, `docs/user-stories.md` |
| `events` | `.claude/agents/events.md` | Define y versiona contratos en `shared-contracts/`, decide claves de partición, documenta reglas de evolución y DLQ. | `docs/arquitectura-c4.md`, `docs/adr/ADR-002-kafka-broker.md` |
| `ml` | `.claude/agents/ml.md` | Solo para `scoring-service`: entrenamiento reproducible, versionado en `model_registry`, SHAP, degradación a solo reglas. | `docs/adr/ADR-007-scoring-reglas-ml-shap.md` |

> Los archivos de los agentes todavía no están escritos. Una vez que existan, el patrón es: cada agente abre primero los documentos de su columna "Lee", luego pide los archivos que va a tocar, y responde en pocas líneas antes de proponer cambios.

---

## 5. Slash commands — `.claude/commands/`

| Comando | Archivo | Para qué |
| --- | --- | --- |
| `/nuevo-servicio <nombre>` | `.claude/commands/nuevo-servicio.md` | Crea un servicio nuevo con la estructura DDD, `pyproject.toml`, `CLAUDE.md` y `state/estado-<nombre>.md`. |

> Pendiente de redactar. Mientras tanto, usa los pasos del `docs/arquitectura-c4.md` §2 como guía manual.

---

## 6. Flujo típico de trabajo

Cuando el usuario pida una feature, sigue este orden:

1. **Ubicar la historia.** Busca en `docs/user-stories.md` la historia que describe lo pedido; respeta sus criterios de aceptación.
2. **Ubicar el servicio.** Mira `docs/arquitectura-c4.md` §2 para saber cuál BC implementa la historia.
3. **Abrir el `CLAUDE.md` del servicio.**
4. **Trabajar de adentro hacia afuera:**
   - Agente `domain`: aggregate, value objects, commands, puerto.
   - Agente `infrastructure`: modelo SQLAlchemy, mapper, repositorio, migración Alembic.
   - Agente `application`: command service con `Result`, event handler si publica.
   - Agente `interfaces`: resource, transform, controller (o consumer).
   - Agente `tests`: cobertura mínima según `docs/requisitos.md` RNF-23.
5. **Actualizar `state/estado-<servicio>.md`** con lo que quedó listo.
6. **Resumen final al usuario:** tres o cuatro líneas, nunca el código completo si ya está en el repo.

---

## 7. Qué no hacer

- No escribir código antes de leer los documentos relacionados.
- No crear carpetas o capas que el servicio no necesite.
- No compartir código entre servicios: `shared-contracts` es solo datos.
- No introducir una dependencia nueva sin anotarlo en el `pyproject.toml` del servicio correspondiente (no en la raíz).
- No cambiar contratos ya publicados sin crear una nueva versión (`V2`).
- No escribir secretos en el repositorio, ni en ejemplos.
- No usar `print` ni `logging` básico: usa logs estructurados JSON con `trace_id`.
- No responder al usuario con el documento abierto completo; cita lo relevante y continúa.

---

## 8. Contexto del autor

- Proyectos previos en Java/Spring Boot: `therapyconnect-platform`, `SkillSwap-WebServices-Java`, `CreditoTiendas`, `learning-center-platform` (base de la guía de arquitectura por capas + DDD).
- Proyectos previos en Python/datos: `pipeline-contrataciones-peru` (pipeline OCDS con SHAP).
- Buscando prácticas pre-profesionales en Lima: Junior Data Engineer, Analista de Riesgos y Fraude, Junior ML Engineer, Backend Jr. en fintech.

FraudShield suma a ese portafolio **mensajería de eventos, DDD distribuido y explicabilidad con SHAP**, y se presenta con una API de analítica como frontera de seguridad hacia Power BI.
