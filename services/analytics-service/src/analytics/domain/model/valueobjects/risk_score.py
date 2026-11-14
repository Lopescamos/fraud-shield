from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskScore:
    """Score 0..100. Duplicated from scoring-service because analytics
    does not depend on scoring."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 0 or self.value > 100:
            raise ValueError("[RiskScore] value must be within 0..100")
