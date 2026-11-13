# Pendientes transversales

Tareas que afectan a dos o más servicios, al repositorio o a la infraestructura. Pendientes de un solo servicio viven en `state/estado-<servicio>.md`.

## Pendiente

- [ ] Levantar Kafka (KRaft) en `infra/docker-compose.yml`: desbloquea encender el relay del outbox en `transaction-service`, `scoring-service` y `alert-service`, el consumer `scoring.assess-transaction` en `scoring-service` y el consumer `alert.raise-on-scored` en `alert-service`. Hasta entonces todas estas piezas quedan implementadas pero apagadas por env var (`*_OUTBOX_RELAY_ENABLED=false`, `SCORING_CONSUMER_ENABLED=false`, `ALERT_CONSUMER_ENABLED=false`).
- [ ] Agregar `scoring-service` y `alert-service` al pipeline CI del monorepo (matrix por servicio: ruff + mypy + lint-imports + pytest). Hoy `transaction-service` ya corre; falta replicar para los dos nuevos.
- [ ] Decidir dónde vive la regla `score -> decision` (APPROVE<40, REVIEW 40..89, BLOCK>=90): hoy está en `scoring-service` (como enum de dominio) y duplicada en `alert-service` (`TransactionScoredConsumer._decision_from_score`). Opciones: promoverla a un campo propio de `TransactionScoredV1` o aceptar el duplicado documentado.
