# ADR-004: PostgreSQL con un esquema y un usuario por servicio

- Estado: Aceptada
- Fecha: 2026-11-10

## Contexto

En microservicios, cada servicio debe ser **dueño de sus datos**: ningún servicio lee o escribe las tablas de otro. La opción más estricta es una instancia de base por servicio; la más laxa es compartir todo bajo un mismo usuario. Buscamos un punto que mantenga el aislamiento sin la operación de cuatro instancias.

## Decisión

Una **sola instancia de PostgreSQL 16** con:

- **Un esquema por servicio**: `tx`, `scoring`, `alerts`, `analytics`.
- **Un usuario de base de datos por servicio**, con `GRANT USAGE, CREATE` solo sobre su esquema y `search_path` fijado a ese esquema.
- Las migraciones (Alembic) viven **dentro del servicio**, nunca en la raíz del monorepo.
- La inicialización de esquemas y usuarios está en `infra/database/postgres/init.sql`.

Un intento de lectura o escritura cruzada es rechazado por el motor, incluso si alguien lo escribe por error.

## Alternativas consideradas

- **Una base por servicio** (cuatro instancias). Aislamiento absoluto, pero cuadriplica los recursos en local sin ganancia para un portafolio.
- **Un solo esquema `public` compartido**. Fácil de arrancar pero rompe la regla de ownership.
- **Base por servicio en otra tecnología** (Mongo para `analytics`, por ejemplo). Añade complejidad sin justificación aquí.

## Consecuencias

- Operación simple (un solo contenedor) con aislamiento efectivo.
- Si un servicio necesita datos de otro los recibe por evento Kafka y mantiene su propia copia (modelo de lectura en `analytics`).
- La migración futura a bases separadas es trivial: cada esquema puede extraerse a su propia base sin rearquitectar.
- El gestor de secretos (hoy `.env` local) debe tener una contraseña por usuario.
