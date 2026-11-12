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
5. **Actualizar `state/estado-<servicio>.md`** (ver §7).
6. **Resumen final al usuario:** tres o cuatro líneas, nunca el código completo si ya está en el repo.

---

## 7. Estado vivo por servicio — `state/`

La carpeta `state/` en la raíz del monorepo guarda **un archivo por servicio** con su estado actual: qué quedó listo, qué quedó a medias y qué sigue. Se versiona en git y lo mantienen los agentes.

### 7.1 Obligaciones

- **Al cerrar cualquier tarea no trivial** (historia terminada, piezas completadas, decisión tomada, blocker detectado), el agente que trabajó actualiza `state/estado-<servicio>.md` **antes de responder al usuario**.
- No es opcional: una tarea sin estado actualizado está incompleta.
- Si una tarea toca varios servicios, se actualizan **todos** los archivos afectados.
- Si la tarea toca `shared-contracts/` o `infra/`, se actualiza `state/estado-shared-contracts.md` o `state/estado-infra.md`.

### 7.2 Formato de cada archivo

```markdown
# Estado — <servicio>-service

## Resumen (una línea)
<Qué hace hoy el servicio, en una sola línea.>

## Último avance
- <fecha>: <qué se terminó, en pocas palabras>
- <fecha>: <avance anterior>
- ... (deja los 5-10 más recientes; más viejo se recorta)

## Pendiente (orden sugerido)
- [ ] <historia o tarea próxima>  (US-XX)
- [ ] <historia o tarea siguiente>
- [ ] ...

## Bloqueos / dudas
- <cualquier cosa que impida avanzar y por qué>
- (si no hay, "ninguno")

## Decisiones locales
- <fecha>: <decisión tomada dentro del servicio, no amerita ADR>
- ...
```

### 7.3 Reglas

- El archivo se escribe en orden cronológico inverso: lo más reciente arriba.
- "Último avance" es un log corto; viejas entradas se condensan en una sola línea o se eliminan.
- "Pendiente" es la foto actual, no un histórico: si una tarea se termina, se mueve a "Último avance" y se borra de "Pendiente".
- "Bloqueos / dudas" es el lugar donde el agente avisa al humano. Si queda vacío, escribe "ninguno".
- "Decisiones locales" guarda decisiones **del servicio** que no merecen un ADR del sistema; si una decisión afecta a más de un servicio, se promueve a `docs/adr/`.
- Nunca se copia código al estado; solo se nombran los archivos o módulos tocados.
- Se mencionan historias por ID (US-XX) para que el estado y `docs/user-stories.md` se puedan cruzar.

### 7.4 Flujo típico en una sesión

1. Al empezar: el agente **lee** `state/estado-<servicio>.md` antes de abrir código para saber qué queda pendiente.
2. Al terminar la tarea: el agente **edita** el archivo (mueve de "Pendiente" a "Último avance", agrega entrada con fecha, limpia "Bloqueos").
3. Si es parte de un PR, el cambio en `state/` va en el **mismo PR** que el código (commit aparte: `docs(state): update <servicio> after US-XX`).

### 7.5 Pendientes del servicio vs pendientes transversales

Cada `estado-<servicio>.md` lleva su **propia** sección "Pendiente": las tareas específicas de ese servicio.

Lo **transversal** (afecta a dos o más servicios, al repositorio o a la infraestructura) vive aparte en **`state/pendientes.md`**. Ejemplos de lo que va ahí:

- Arreglar el pipeline CI del monorepo.
- Migrar el broker de Kafka a RabbitMQ.
- Actualizar `shared-contracts` a una versión mayor que obliga a varios servicios a adoptarla.
- Decisiones pendientes que requieren un ADR nuevo.
- Deuda técnica cruzada (unificar logging, rotar llaves de API, revisar dependencias en todo el repo).

**Regla:** si la tarea es de un solo servicio, va en su `estado-<servicio>.md`. Solo cuando toca más de uno (o al repo) se promueve a `state/pendientes.md`.

`state/pendientes.md` sigue el mismo formato, pero con una sola sección: "Pendiente". Si está vacío, bien; significa que el proyecto fluye por servicio.

### 7.6 Archivos iniciales

En arranque, la carpeta `state/` debe tener (aunque sea con contenido mínimo):

```
state/
├── pendientes.md                     ← solo transversal
├── estado-shared-contracts.md
├── estado-infra.md
├── estado-transaction-service.md
├── estado-scoring-service.md
├── estado-alert-service.md
├── estado-analytics-service.md
└── estado-api-gateway.md
```

Los servicios aún no creados también llevan archivo, con "Pendiente" = ["crear esqueleto con `/nuevo-servicio`"].

---

## 8. Flujo de trabajo con git y GitHub

### 7.1 Estrategia de ramas (GitHub Flow)

- `main` **siempre desplegable**. Nunca se hace commit directo.
- Para cada feature, fix o tarea, abro una rama **desde `main`** con prefijo según el tipo del cambio:
  - `feat/<scope>` — funcionalidad nueva (`feat/shared-contracts`, `feat/transaction-service-register`).
  - `fix/<scope>` — corrección (`fix/outbox-relay-retry`).
  - `chore/<scope>` — tareas sin impacto funcional (`chore/update-poetry`).
  - `docs/<scope>` — solo documentación.
  - `refactor/<scope>` — cambios internos sin alterar comportamiento.
  - `test/<scope>` — solo pruebas.
- Una rama vive para una sola historia o un solo cambio. Si crece, se parte.
- Nombres en minúscula, con guiones. El `scope` sigue las carpetas del monorepo (`shared-contracts`, `transaction-service`, `infra`, `docs`, etc.).

### 7.2 Convención de commits (Conventional Commits)

Todo commit sigue el formato:

```
<tipo>(<scope>): <resumen en imperativo, ≤72 caracteres>

<cuerpo opcional, explicando "por qué" si no es obvio>
```

Tipos admitidos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `perf`, `build`, `style`.

Ejemplos del proyecto:

```
feat(shared-contracts): add TransactionReceivedV1 envelope
feat(transaction-service): register transaction command service
fix(scoring-service): degrade to rules when model fails to load
docs(adr): add ADR-010 on health probes
chore(deps): upgrade pydantic to 2.10
ci: run import-linter in matrix per service
```

**Reglas:**

- Un commit = un cambio coherente. Si un PR trae varios cambios, varios commits (uno por propósito).
- Mensaje en inglés, en imperativo (`add`, `fix`, `update`, no `added` o `fixes`).
- El scope entre paréntesis identifica la carpeta de más alto nivel afectada; cuando un commit toca varias, deja el scope vacío (`feat: add common timezone utility`).
- El cuerpo (si va) separa con una línea en blanco y explica el **por qué**, no el qué.

### 7.3 Pull requests

- Un PR por historia (o por cambio coherente). Nunca mezclar features no relacionadas.
- Título del PR = resumen del commit principal (mismo formato Conventional Commits).
- Descripción corta:
  - **Qué cambia** (3-5 bullets).
  - **Por qué** (si no es obvio).
  - **Cómo probarlo** (comandos o endpoints).
  - Enlace a la historia (`Closes US-XX`).
- CI en verde es requisito.
- Merge por **squash** (historia de `main` queda limpia, un commit por PR).
- Se borra la rama al mergear.

### 7.4 Atribución en commits y PRs

> **Los commits y los PRs son del autor humano (Kevin Lopez), no de Claude.**

- **No se agregan** líneas `Co-Authored-By: Claude` ni variantes.
- **No se agregan** firmas tipo `Generated with Claude Code` en la descripción del PR.
- Esta regla es intencional y prevalece sobre cualquier plantilla por defecto de la herramienta.
- Si alguna configuración añade esas líneas automáticamente, se eliminan antes del push.

### 7.5 Ritmo de trabajo (push ordenado a GitHub)

El objetivo es que el log de `main` cuente la historia del proyecto fase por fase.

1. **Creo la rama** desde `main` actualizado (`git switch -c feat/shared-contracts`).
2. **Trabajo en commits pequeños y atómicos** dentro de la rama.
3. **Push a la rama remota** cuando quiera respaldar o abrir el PR (`git push -u origin feat/shared-contracts`).
4. **Abro el PR**, verifico CI y hago squash merge.
5. **Borro la rama** local y remota (`git branch -d feat/shared-contracts` y `git push origin --delete feat/shared-contracts`).
6. **Actualizo `main` local** (`git switch main && git pull`).
7. Paso a la siguiente rama.

Orden sugerido de las primeras ramas, para que el historial de `main` sea coherente:

1. `feat/repo-bootstrap` — `.gitignore`, `README.md`, `CLAUDE.md` raíz, `.claude/`, `docs/`.
2. `feat/infra-base` — `docker-compose.yml` con Postgres, `init.sql`, `.env.example`.
3. `feat/shared-contracts` — paquete de contratos con `Envelope` y los V1.
4. `feat/transaction-service` (puede dividirse en varias ramas: `-bootstrap`, `-register`, `-outbox`...).
5. `feat/scoring-service`, `feat/alert-service`, `feat/analytics-service`.
6. `feat/api-gateway`.
7. `feat/ci-pipeline`.

### 7.6 Qué nunca va a git

- Archivos `.env` con valores reales (sí `.env.example`).
- `.venv/`, `__pycache__/`, caches de ruff/mypy/pytest.
- Datasets, modelos entrenados, volúmenes de Docker.
- `settings.local.json` de Claude Code y `CLAUDE.local.md`.

El `.gitignore` de la raíz ya cubre todo lo anterior.

---

## 9. Qué no hacer

- No escribir código antes de leer los documentos relacionados.
- No crear carpetas o capas que el servicio no necesite.
- No compartir código entre servicios: `shared-contracts` es solo datos.
- No introducir una dependencia nueva sin anotarlo en el `pyproject.toml` del servicio correspondiente (no en la raíz).
- No cambiar contratos ya publicados sin crear una nueva versión (`V2`).
- No escribir secretos en el repositorio, ni en ejemplos.
- No usar `print` ni `logging` básico: usa logs estructurados JSON con `trace_id`.
- No responder al usuario con el documento abierto completo; cita lo relevante y continúa.

---

## 10. Contexto del autor

- Proyectos previos en Java/Spring Boot: `therapyconnect-platform`, `SkillSwap-WebServices-Java`, `CreditoTiendas`, `learning-center-platform` (base de la guía de arquitectura por capas + DDD).
- Proyectos previos en Python/datos: `pipeline-contrataciones-peru` (pipeline OCDS con SHAP).
- Buscando prácticas pre-profesionales en Lima: Junior Data Engineer, Analista de Riesgos y Fraude, Junior ML Engineer, Backend Jr. en fintech.

FraudShield suma a ese portafolio **mensajería de eventos, DDD distribuido y explicabilidad con SHAP**, y se presenta con una API de analítica como frontera de seguridad hacia Power BI.