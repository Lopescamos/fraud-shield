from __future__ import annotations

import logging
from typing import Any

from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.domain.model.valueobjects.risk_factor import RiskFactor
from scoring.domain.services.explainer import Explainer
from scoring.infrastructure.ml.features import FEATURE_NAMES, vectorize

logger = logging.getLogger(__name__)


class ShapExplainer(Explainer):
    """
    TreeExplainer over the XGBoost booster. Only enabled when the booster
    is available; otherwise ``is_available`` returns False and the
    application layer skips SHAP.
    """

    def __init__(
        self,
        tree_explainer: Any | None,
        feature_names: list[str] | None = None,
    ) -> None:
        self._explainer = tree_explainer
        self._feature_names = feature_names or FEATURE_NAMES

    @classmethod
    def from_booster(cls, booster: Any | None) -> ShapExplainer:
        if booster is None:
            return cls(None)
        try:
            import shap
            return cls(shap.TreeExplainer(booster))
        except Exception:
            logger.exception("shap-init-failed")
            return cls(None)

    def is_available(self) -> bool:
        return self._explainer is not None

    async def top_factors(
        self, command: ScoreTransactionCommand, top_n: int = 3
    ) -> list[RiskFactor]:
        if self._explainer is None:
            return []
        features = vectorize(command)
        shap_values = self._explainer.shap_values([features])[0]
        pairs = sorted(
            zip(self._feature_names, shap_values, strict=False),
            key=lambda item: abs(float(item[1])),
            reverse=True,
        )[:top_n]
        return [
            RiskFactor(
                feature=name,
                weight=float(value),
                direction="increase" if float(value) > 0 else "decrease",
                source="shap",
            )
            for name, value in pairs
        ]
