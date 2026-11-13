from __future__ import annotations

from typing import Protocol

from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.domain.model.valueobjects.risk_factor import RiskFactor


class RuleEngine(Protocol):
    """
    Evaluates all active rules against a transaction and returns the
    combined score (0..100) plus the hit list as risk factors. Lives as a
    port in application so the adapter can read rules from YAML, DB, or
    somewhere else.
    """

    async def evaluate(
        self, command: ScoreTransactionCommand
    ) -> tuple[int, list[RiskFactor]]: ...
