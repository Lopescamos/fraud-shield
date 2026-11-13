from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskScore:
    value: float

    def __post_init__(self) -> None:
        if not (0.0 <= float(self.value) <= 100.0):
            raise ValueError("[RiskScore] value must be between 0 and 100")

    def as_int(self) -> int:
        return int(round(self.value))
