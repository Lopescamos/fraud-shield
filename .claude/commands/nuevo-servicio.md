---
description: Crea un servicio nuevo con la estructura DDD + hexagonal del monorepo. Uso. /nuevo-servicio <nombre-sin-sufijo>. Ejemplo. /nuevo-servicio scoring
---

# /nuevo-servicio

Cuando el usuario invoque este comando, sigue estos pasos tal cual. El argumento es el **nombre corto** (sin `-service`): `scoring`, `alert`, `analytics`, etc.

## 1. Validación

- Rechaza si el argumento viene vacío o si incluye caracteres fuera de `[a-z0-9-]`.
- Rechaza si ya existe `services/<nombre>-service/`.
- Si `nombre` tiene guion, el paquete Python será `nombre_con_guion_bajo` (ej. `api-gateway` → `api_gateway`). Si no tiene guion, el paquete es el mismo nombre (`scoring` → `scoring`).

## 2. Variables derivadas

```
service_dir   = services/<nombre>-service
package_name  = nombre con '-' → '_'
schema_name   = nombre sin '_'   (ej. para api_gateway usar 'api_gateway'; para scoring usar 'scoring')
app_title     = <Nombre con mayúscula> Service
env_prefix    = <NOMBRE_EN_MAYUSCULA_CON_GUION_BAJO>_
```

## 3. Crear carpetas (vacías con `__init__.py` cuando corresponda)

```
services/<nombre>-service/
├── CLAUDE.md
├── pyproject.toml
├── Dockerfile
├── alembic.ini
├── .env.example
├── migrations/
│   ├── env.py
│   └── versions/.gitkeep
├── src/<package_name>/
│   ├── __init__.py
│   ├── main.py
│   ├── kernel/{__init__.py, application/__init__.py, domain/__init__.py, messaging/__init__.py}
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── model/{__init__.py, aggregates/__init__.py, valueobjects/__init__.py,
│   │   │          commands/__init__.py, queries/__init__.py, events/__init__.py}
│   │   ├── repositories/__init__.py
│   │   └── services/__init__.py
│   ├── application/
│   │   ├── __init__.py
│   │   ├── commandservices/__init__.py
│   │   ├── queryservices/__init__.py
│   │   └── internal/{__init__.py, commandservices/__init__.py, queryservices/__init__.py,
│   │                 eventhandlers/__init__.py,
│   │                 outboundservices/{__init__.py, messaging/__init__.py}}
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── persistence/{__init__.py, entities/__init__.py, assemblers/__init__.py,
│   │   │                repositories/__init__.py, session.py}
│   │   ├── messaging/{__init__.py, outbox/__init__.py, kafka/__init__.py}
│   │   └── config/{__init__.py, settings.py}
│   └── interfaces/
│       ├── __init__.py
│       ├── rest/{__init__.py, resources/__init__.py, transform/__init__.py}
│       └── messaging/{__init__.py, consumers/__init__.py, transform/__init__.py}
└── tests/
    ├── conftest.py
    ├── unit/{__init__.py, domain/__init__.py, application/__init__.py}
    ├── integration/{__init__.py, persistence/__init__.py, messaging/__init__.py}
    ├── contract/__init__.py
    ├── interfaces/{__init__.py, rest/__init__.py, messaging/__init__.py}
    └── architecture/test_import_linter.py
```

## 4. Archivos con contenido

### `pyproject.toml`

```toml
[tool.poetry]
name = "<nombre>-service"
version = "0.1.0"
description = "<Nombre> microservice of FraudShield"
authors = ["Kevin Lopez <lopezmontalvokevin2021@gmail.com>"]
packages = [{ include = "<package_name>", from = "src" }]

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.115"
uvicorn = { extras = ["standard"], version = "^0.32" }
pydantic = "^2.9"
pydantic-settings = "^2.6"
sqlalchemy = { extras = ["asyncio"], version = "^2.0" }
asyncpg = "^0.30"
alembic = "^1.14"
aiokafka = "^0.12"
apscheduler = "^3.10"
shared-contracts = { path = "../../shared-contracts", develop = true }

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"
pytest-asyncio = "^0.24"
pytest-cov = "^6.0"
httpx = "^0.28"
testcontainers = "^4.9"
ruff = "^0.9"
mypy = "^1.13"
import-linter = "^2.1"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "-ra --strict-markers --cov=src --cov-report=term-missing"
testpaths = ["tests"]

[tool.ruff]
line-length = 100

[tool.mypy]
python_version = "3.12"
strict = true
```

### `src/<package_name>/main.py`

```python
from fastapi import FastAPI

app = FastAPI(title="<app_title>", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "UP"}
```

### `src/<package_name>/infrastructure/config/settings.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="<env_prefix>")

    database_url: str
    kafka_bootstrap_servers: str
    log_level: str = "INFO"


settings = Settings()
```

### `.env.example`

```
<env_prefix>DATABASE_URL=postgresql+asyncpg://<package_name>_user:dev@localhost:5432/fraudshield
<env_prefix>KAFKA_BOOTSTRAP_SERVERS=localhost:9092
<env_prefix>LOG_LEVEL=INFO
```

### `alembic.ini` (mínimo)

```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql+asyncpg://<package_name>_user:dev@localhost:5432/fraudshield

[loggers]
keys = root
[handlers]
keys = console
[formatters]
keys = default
[logger_root]
level = INFO
handlers = console
[handler_console]
class = StreamHandler
args = (sys.stderr,)
formatter = default
[formatter_default]
format = %(levelname)s [%(name)s] %(message)s
```

### `Dockerfile` (simple, dos etapas)

```dockerfile
FROM python:3.12-slim AS build
WORKDIR /app
RUN pip install --no-cache-dir poetry==2.0.1
COPY pyproject.toml ./
RUN poetry config virtualenvs.create false && poetry install --only=main --no-root

FROM python:3.12-slim
WORKDIR /app
COPY --from=build /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=build /usr/local/bin /usr/local/bin
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN useradd -m app && chown -R app /app
USER app
CMD ["uvicorn", "<package_name>.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `.importlinter`

```ini
[importlinter]
root_package = <package_name>
include_external_packages = True

[importlinter:contract:layers]
name = Layers of DDD point inward
type = layers
layers =
    <package_name>.interfaces
    <package_name>.infrastructure
    <package_name>.application
    <package_name>.domain

[importlinter:contract:domain-pure]
name = Domain does not depend on frameworks
type = forbidden
source_modules =
    <package_name>.domain
forbidden_modules =
    fastapi
    sqlalchemy
    aiokafka
    pydantic
    shared_contracts
```

### `CLAUDE.md` del servicio

```markdown
# <Nombre> service — CLAUDE.md

## 1. Rol en el sistema
<Describir en 2-3 líneas qué BC implementa este servicio y qué agregados contiene.>

## 2. Lenguaje ubicuo
Lista los términos propios de este contexto (al estilo del glosario de DDD).

## 3. Agregados
- `<Aggregate>` — <una línea sobre su invariante principal>

## 4. Mensajes
### Consume
- `<ContratoVn>` (grupo `<grupo>`)
### Publica
- `<ContratoVn>` en `<canal>`

## 5. Endpoints
- `<Método> <ruta>` — <una línea>

## 6. Reglas específicas
<Reglas de negocio importantes propias de este servicio.>

## 7. Referencias
- Historias: US-XX, US-YY (ver `docs/user-stories.md`)
- ADRs relacionados: ADR-XX
```

### `state/estado-<nombre>.md` (en la raíz del monorepo)

Crear archivo con contenido inicial:

```markdown
# Estado — <nombre>-service

## Resumen
Servicio recién creado con el esqueleto de `/nuevo-servicio`. Todavía no implementa historias.

## Último avance
- <fecha>: estructura de carpetas, pyproject, Dockerfile y .env.example.

## Pendiente
- Primera historia según `docs/user-stories.md`.
- Migración inicial Alembic.
- Tests arquitectura con import-linter.

## Decisiones locales
(ninguna por ahora)
```

## 5. Ajustes al monorepo

- Añadir una entrada al `infra/docker-compose.yml` con el servicio apagado (comentado) y un `TODO` para habilitarlo.
- Añadir una línea en `infra/database/postgres/init.sql` creando el esquema y el usuario del servicio.
- Añadir el servicio a `docs/arquitectura-c4.md` §2 (tabla de contenedores).
- Añadir una tabla al esquema del servicio en `docs/modelo-datos.md`.

## 6. Comandos a correr (desde la raíz)

```powershell
cd services/<nombre>-service
poetry install
poetry run uvicorn <package_name>.main:app --port <puerto>
```

Y confirmar que `curl http://localhost:<puerto>/health` responde `{"status":"UP"}`.

## 7. Qué dejar al usuario

- Un resumen en 4-6 líneas: qué se creó, puerto propuesto, qué falta configurar (DATABASE_URL, Kafka).
- Un enlace mental a los agentes: "para el dominio, llama `@domain`; para la persistencia, `@infrastructure`".
- Recordar que **no se crean carpetas que el servicio no necesite**; borrar las vacías si ya se sabe que no harán falta (p. ej. `interfaces/messaging/` en un servicio que no consume).

## 8. Qué NO hacer

- No crear carpetas fuera de las listadas.
- No agregar código de negocio: solo el esqueleto.
- No instalar dependencias extra que no están en el `pyproject.toml` base.
- No modificar `shared-contracts` ni los otros servicios.
