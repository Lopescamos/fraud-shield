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


class XGBoostRiskModel(RiskModel):
    """
    XGBoost adapter. If the configured model file is missing or fails to
    load, ``is_available`` returns False and the service degrades to
    rules-only without crashing on startup.
    """

    def __init__(self, booster: Any | None, version: str) -> None:
        self._booster = booster
        self._version = version

    @classmethod
    def load_or_degrade(cls, path: str | None, version: str) -> XGBoostRiskModel:
        if not path:
            logger.warning("xgb-path-empty-degrading")
            return cls(None, "rules-only")
        model_file = Path(path)
        if not model_file.exists():
            logger.warning("xgb-model-not-found-degrading", extra={"path": path})
            return cls(None, "rules-only")
        try:
            import xgboost as xgb
            booster = xgb.Booster()
            booster.load_model(str(model_file))
            return cls(booster, version)
        except Exception:
            logger.exception("xgb-load-failed-degrading")
            return cls(None, "rules-only")

    def is_available(self) -> bool:
        return self._booster is not None

    async def score(self, command: ScoreTransactionCommand) -> float:
        if self._booster is None:
            return 0.0
        import xgboost as xgb
        features = vectorize(command)
        dmatrix = xgb.DMatrix([features])
        return float(self._booster.predict(dmatrix)[0])

    def version(self) -> str:
        return self._version
