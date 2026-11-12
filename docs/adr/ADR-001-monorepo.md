# ADR-001: Monorepo por producto

- Estado: Aceptada
- Fecha: 2026-11-10

## Contexto

FraudShield es un sistema de microservicios con cuatro servicios Python/FastAPI, un gateway, un paquete de contratos compartidos y configuración de infraestructura. Cada servicio es desplegable por separado, pero siempre se desarrolla, versiona y libera como un solo producto.

Se evaluó mantener cada servicio en su propio repositorio GitHub (multirepo) o reunirlos en un solo repositorio (monorepo).

## Decisión

El proyecto vive en **un solo repositorio GitHub** (`github.com/Lopescamos/fraudshield`) con la siguiente raíz:

```
fraudshield/
├── services/<servicio>/     (uno por microservicio)
├── shared-contracts/
├── infra/
├── docs/
├── state/
├── .claude/
└── .github/workflows/
```

Cada servicio mantiene su propio `pyproject.toml`, su `.venv`, sus migraciones Alembic y su `Dockerfile`. Ningún servicio importa código de otro; el único módulo compartido es `shared-contracts`.

## Alternativas consideradas

- **Multirepo** (un repo por servicio). Cada servicio con su ciclo propio, útil cuando equipos distintos liberan sin coordinarse. Descartado porque aquí el autor es uno solo, los cambios suelen tocar varios servicios y un PR único ahorra coordinación.
- **Monorepo con Nx/Bazel**. Herramienta pensada para monorepos grandes con grafo de tareas. Descartado por sobrecarga para un proyecto de portafolio.

## Consecuencias

- Un solo clon y un solo workflow de CI; cambios cross-servicio en un PR.
- El aislamiento no se pierde: queda en el runtime (contenedor por servicio), los datos (un esquema y un usuario por servicio) y el código (cada servicio con su `pyproject.toml` y su `.venv`).
- El CI debe detectar qué servicios cambiaron para no correr todo en cada PR (matriz por carpeta).
- Si en el futuro un servicio migra a Java o a otro equipo, se extrae a su propio repo sin reescribir.
