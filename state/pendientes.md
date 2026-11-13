# Pendientes transversales

Tareas que afectan a dos o más servicios, al repositorio o a la infraestructura. Pendientes de un solo servicio viven en `state/estado-<servicio>.md`.

## Pendiente

- [ ] Levantar Kafka (KRaft) en `infra/docker-compose.yml`: desbloquea encender el relay del outbox en `transaction-service` y en `scoring-service`, y el consumer de `transactions.received.v1` en `scoring-service`. Hasta entonces los tres piezas quedan implementadas pero apagadas por env var (`*_OUTBOX_RELAY_ENABLED=false`, `SCORING_CONSUMER_ENABLED=false`).
- [ ] Agregar `scoring-service` al pipeline CI del monorepo (matrix por servicio: ruff + mypy + lint-imports + pytest). Hoy `transaction-service` ya corre; falta replicar para el nuevo servicio.
