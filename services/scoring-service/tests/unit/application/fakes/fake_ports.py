from __future__ import annotations

from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.domain.model.valueobjects.risk_factor import RiskFactor


class StaticRuleEngine:
    def __init__(self, score: int, factors: list[RiskFactor] | None = None) -> None:
        self._score = score
        self._factors = factors or []
        self.calls = 0

    async def evaluate(
        self, command: ScoreTransactionCommand
    ) -> tuple[int, list[RiskFactor]]:
        self.calls += 1
        return self._score, list(self._factors)


class FailingRuleEngine:
    async def evaluate(self, command: ScoreTransactionCommand):
        raise RuntimeError("rules-down")


class StaticRiskModel:
    def __init__(self, available: bool, score: float = 0.0, version: str = "test-v1") -> None:
        self._available = available
        self._score = score
        self._version = version

    def is_available(self) -> bool:
        return self._available

    async def score(self, command: ScoreTransactionCommand) -> float:
        return self._score

    def version(self) -> str:
        return self._version


class ThrowingRiskModel:
    def __init__(self, version: str = "boom-v1") -> None:
        self._version = version

    def is_available(self) -> bool:
        return True

    async def score(self, command: ScoreTransactionCommand) -> float:
        raise RuntimeError("model-explode")

    def version(self) -> str:
        return self._version


class StaticExplainer:
    def __init__(self, available: bool, factors: list[RiskFactor] | None = None) -> None:
        self._available = available
        self._factors = factors or []
        self.calls = 0

    def is_available(self) -> bool:
        return self._available

    async def top_factors(
        self, command: ScoreTransactionCommand, top_n: int = 3
    ) -> list[RiskFactor]:
        self.calls += 1
        return list(self._factors)[:top_n]
