from __future__ import annotations

from typing import Protocol

from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)


class RiskModel(Protocol):
    """
    Port for a risk-scoring model. Implementations live in
    ``infrastructure/ml/`` (xgboost, isolation forest). ``is_available``
    tells the application whether to use it or fall back to rules-only.
    """

    def is_available(self) -> bool: ...

    async def score(self, command: ScoreTransactionCommand) -> float: ...

    def version(self) -> str: ...
