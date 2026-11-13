from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.domain.services.risk_model import RiskModel
from scoring.infrastructure.ml.features import vectorize

logger = logging.getLogger(__name__)


class IsolationForestRiskModel(RiskModel):
    """
    Isolation Forest adapter. Same degradation protocol as XGBoost: a
    missing model file leaves the service running rules-only.
    """

    def __init__(self, model: Any | None, version: str) -> None:
        self._model = model
        self._version = version

    @classmethod
    def load_or_degrade(cls, path: str | None, version: str) -> IsolationForestRiskModel:
        if not path:
            logger.warning("iforest-path-empty-degrading")
            return cls(None, "rules-only")
        model_file = Path(path)
        if not model_file.exists():
            logger.warning(
                "iforest-model-not-found-degrading", extra={"path": path}
            )
            return cls(None, "rules-only")
        try:
            import joblib
            model = joblib.load(str(model_file))
            return cls(model, version)
        except Exception:
            logger.exception("iforest-load-failed-degrading")
            return cls(None, "rules-only")

    def is_available(self) -> bool:
        return self._model is not None

    async def score(self, command: ScoreTransactionCommand) -> float:
        if self._model is None:
            return 0.0
        features = vectorize(command)
        raw = float(self._model.decision_function([features])[0])
        # Normalize: more negative = more anomalous => higher anomaly score.
        value = 0.5 - raw
        return max(0.0, min(1.0, value))

    def version(self) -> str:
        return self._version
