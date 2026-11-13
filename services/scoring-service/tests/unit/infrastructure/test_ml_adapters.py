from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.infrastructure.ml.features import FEATURE_NAMES, vectorize
from scoring.infrastructure.ml.isolation_forest_risk_model import (
    IsolationForestRiskModel,
)
from scoring.infrastructure.ml.shap_explainer import ShapExplainer
from scoring.infrastructure.ml.xgboost_risk_model import XGBoostRiskModel


def _cmd() -> ScoreTransactionCommand:
    return ScoreTransactionCommand(
        transaction_id=uuid4(),
        account_id_hash="a" * 64,
        amount=Decimal("500.00"),
        currency="PEN",
        channel="WEB",
        occurred_at=datetime(2026, 11, 13, 13, 0, tzinfo=UTC),
        extra_features={
            "tx_count_last_5m": 2.0,
            "new_device": 0.0,
            "amount_ratio_vs_avg": 1.3,
        },
    )


def test_feature_vector_length_matches_names() -> None:
    v = vectorize(_cmd())
    assert len(v) == len(FEATURE_NAMES)


def test_xgb_degrades_when_path_is_empty() -> None:
    model = XGBoostRiskModel.load_or_degrade(path=None, version="v1")
    assert model.is_available() is False
    assert model.version() == "rules-only"


def test_xgb_degrades_when_path_missing() -> None:
    model = XGBoostRiskModel.load_or_degrade(
        path="/path/does/not/exist/xgb.json", version="v1"
    )
    assert model.is_available() is False


@pytest.mark.asyncio
async def test_xgb_score_returns_zero_in_degraded_mode() -> None:
    model = XGBoostRiskModel.load_or_degrade(path=None, version="v1")
    assert await model.score(_cmd()) == 0.0


def test_iforest_degrades_when_path_is_empty() -> None:
    model = IsolationForestRiskModel.load_or_degrade(path=None, version="v1")
    assert model.is_available() is False


def test_iforest_degrades_when_path_missing() -> None:
    model = IsolationForestRiskModel.load_or_degrade(
        path="/path/does/not/exist/iforest.joblib", version="v1"
    )
    assert model.is_available() is False


def test_shap_explainer_unavailable_without_booster() -> None:
    explainer = ShapExplainer.from_booster(None)
    assert explainer.is_available() is False


@pytest.mark.asyncio
async def test_shap_top_factors_empty_in_degraded_mode() -> None:
    explainer = ShapExplainer.from_booster(None)
    assert await explainer.top_factors(_cmd()) == []
