from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskFactor:
    """A single contribution to a ScoringResult. Used for both rule hits
    (``source='rule'``) and SHAP features (``source='shap'``)."""

    feature: str
    weight: float
    direction: str
    source: str = "shap"

    def __post_init__(self) -> None:
        if not self.feature or not self.feature.strip():
            raise ValueError("[RiskFactor] feature cannot be empty")
        if self.direction not in {"increase", "decrease", "neutral"}:
            raise ValueError(
                "[RiskFactor] direction must be 'increase', 'decrease' or 'neutral'"
            )
        if self.source not in {"rule", "shap"}:
            raise ValueError("[RiskFactor] source must be 'rule' or 'shap'")
