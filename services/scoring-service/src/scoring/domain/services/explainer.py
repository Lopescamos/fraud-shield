from __future__ import annotations

from typing import Protocol

from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.domain.model.valueobjects.risk_factor import RiskFactor


class Explainer(Protocol):
    """Port for explainability. SHAP implementation lives in infrastructure."""

    def is_available(self) -> bool: ...

    async def top_factors(
        self, command: ScoreTransactionCommand, top_n: int = 3
    ) -> list[RiskFactor]: ...
