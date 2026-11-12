# ADR-005: Identificadores generados por el dominio (UUID)

- Estado: Aceptada
- Fecha: 2026-11-10

## Contexto

En un sistema orientado a eventos con Outbox, el evento que publica un servicio debe ir con el `id` del aggregate **antes** del `COMMIT`: si el `id` dependiera de un autoincremental, no se podría armar el evento en la misma transacción que la persistencia.

## Decisión

Los identificadores de negocio (`transaction_id`, `assessment_id`, `alert_id`, `message_id`) son **UUID generados en el dominio** al crear el aggregate. La tabla sigue teniendo una clave técnica `BIGSERIAL` como PK para los índices, pero el `uuid` es `UNIQUE` y es el que viaja en eventos y APIs.

El UUID se genera con `uuid4()` (random). No usamos la columna `id` autoincremental para identificar fuera del servicio.

## Alternativas consideradas

- **`BIGSERIAL` autoincremental**. Natural con SQLAlchemy, pero obliga a `flush()` antes de publicar el evento y rompe la transaccionalidad del Outbox.
- **ULID / TSID** (ordenables en el tiempo). Mejor para índices B-tree que UUID v4, pero añaden dependencia y el beneficio en este tamaño no justifica el costo.
- **Secuencias Postgres manuales**. No portables si algún servicio migra a otra base.

## Consecuencias

- Los Assemblers dejan de usar el truco `if id != null` que había en la guía Java: el `id` siempre existe.
- Con ID asignado (no autogenerado por la base), SQLAlchemy hace `merge` al guardar (un `SELECT` previo). Aceptable para el volumen del proyecto.
- Los UUID no son ordenables en el tiempo; donde haga falta orden por llegada, hay `created_at` o `occurred_at`.
