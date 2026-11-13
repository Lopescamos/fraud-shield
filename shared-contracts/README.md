# shared-contracts

Contratos de mensajes de FraudShield: `Envelope`, eventos versionados (`V1`) y
constantes de canales/grupos/DLQ. Cero lógica, cero dependencias de SQLAlchemy,
FastAPI ni Kafka. Solo Pydantic v2.

Es el único paquete del monorepo que puede ser importado por varios servicios.
Convenciones y reglas de evolución: ver `.claude/agents/events.md` y
`docs/contrato-api.md` §4.

## Instalación desde un servicio

En el `pyproject.toml` del servicio consumidor:

```toml
[tool.poetry.dependencies]
shared-contracts = { path = "../../shared-contracts", develop = true }
```

Luego `poetry lock && poetry install`.

## Uso

```python
from shared_contracts.envelope import Envelope
from shared_contracts.transactions.v1 import TransactionReceivedV1
from shared_contracts.constants import TRANSACTIONS_RECEIVED_V1, dlq_of

env = Envelope[TransactionReceivedV1].model_validate(raw_message)
topic = TRANSACTIONS_RECEIVED_V1
dlq = dlq_of("scoring.assess-transaction")
```

## Reglas rápidas

- Cada contrato lleva sufijo `V<n>` y su canal `.v<n>`.
- `model_config = ConfigDict(extra="ignore", frozen=True)`.
- Cambios compatibles (campo opcional) → misma versión.
- Cambios incompatibles → nueva versión `V<n+1>` y publicación paralela.
- Nombres de canales/grupos/DLQ viven en `constants.py`, nunca como literales sueltos.

## Desarrollo

```bash
poetry install
poetry run pytest -q
poetry run ruff check .
```
