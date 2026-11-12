# ADR-003: Python 3.12 + FastAPI como stack base

- Estado: Aceptada
- Fecha: 2026-11-10

## Contexto

El proyecto usa DDD y arquitectura hexagonal, y la parte de scoring necesita librerías de Machine Learning con buen soporte (XGBoost, Isolation Forest, SHAP). El autor viene de proyectos en Java/Spring Boot (CreditoTiendas, SkillSwap) y quiere ampliar su portafolio con Python manteniendo la misma rigurosidad arquitectónica.

## Decisión

Stack base para todos los servicios:

- **Python 3.12** administrado con **Poetry 2.x** (un `pyproject.toml` y un `.venv` por servicio).
- **FastAPI** para la capa HTTP; **Pydantic v2** para validación y modelos; **SQLAlchemy 2 async** + **asyncpg** para persistencia; **Alembic** para migraciones; **AIOKafka** para mensajería.
- Para ML: **XGBoost**, **scikit-learn** (Isolation Forest), **SHAP**.
- Para calidad: **ruff** (linter + formatter), **mypy** (tipos), **pytest** + **pytest-asyncio** + **testcontainers** + **httpx** para tests.

**Deja la puerta abierta**: si algún servicio necesita saltar a Java/Spring Boot en el futuro, puede hacerlo porque la frontera entre servicios son contratos de eventos (`shared-contracts`), no librerías compartidas de código.

## Alternativas consideradas

- **Java 21 + Spring Boot** para todos los servicios. Es lo que el autor domina mejor, pero duplicaría el enfoque de sus proyectos anteriores. Descartado para este proyecto; se conserva la guía DDD en Java como referencia general.
- **Node.js + NestJS**. Buen soporte HTTP, pero el ecosistema de ML en Python es mejor y aquí pesa.
- **Go**. Excelente para microservicios y buen rendimiento, pero el ecosistema de ML y SHAP es mucho más débil.

## Consecuencias

- Un solo lenguaje y un solo gestor de dependencias en todo el repositorio.
- Las reglas de nomenclatura siguen PEP 8: paquetes sin guiones (`transaction`, `api_gateway`), módulos y archivos en `snake_case`, clases en `PascalCase`.
- El servicio de scoring puede cargar modelos ONNX/pickle directamente, sin necesidad de un servicio aparte de ML.
- El manejo de concurrencia en FastAPI exige disciplina con `async/await` y sesiones de SQLAlchemy async; se cubre con guidelines en `CLAUDE.md`.
