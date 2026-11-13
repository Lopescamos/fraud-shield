# Estado — shared-contracts

## Resumen (una línea)
Paquete Python (Poetry 2) con el Envelope, los eventos V1 (transactions y alerts) y las constantes de canales/grupos/DLQ.

## Último avance
- 2026-11-12: scaffold del proyecto Poetry 2 (`pyproject.toml`, `README.md`, `.gitignore`).
- 2026-11-12: `envelope.py` genérico `Envelope[P]` con `extra="ignore"` y `constants.py` con canales, grupos de consumo y helper `dlq_of`.
- 2026-11-12: contratos `TransactionReceivedV1` y `TransactionScoredV1` en `transactions/v1/`.
- 2026-11-12: contratos `AlertRaisedV1` y `AlertResolvedV1` en `alerts/v1/`.
- 2026-11-12: tests de contrato con roundtrip y tolerancia a campos desconocidos para los cuatro eventos (`poetry run pytest -q` → 11 OK, `ruff check .` limpio).

## Pendiente (orden sugerido)
- [ ] Integrar `shared-contracts` como dependencia `path` desde el primer servicio que lo consuma (transaction-service) y validar el import.

## Bloqueos / dudas
- ninguno

## Decisiones locales
- 2026-11-12: `TransactionScoredV1`, `AlertRaisedV1` y `AlertResolvedV1` derivan sus campos de `docs/modelo-datos.md` (tablas `scoring.risk_assessments`, `alerts.fraud_alerts`, `alerts.alert_status_history`). El único ejemplo explícito en `docs/contrato-api.md` §4.2 es `TransactionReceivedV1`.
- 2026-11-12: `poetry.lock` se versiona para reproducibilidad del CI.
