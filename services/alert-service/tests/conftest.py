from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from alert.domain.model.commands.raise_alert_from_score_command import (
    RaiseAlertFromScoreCommand,
)
from alert.domain.model.valueobjects.risk_factor import RiskFactor


@pytest.fixture
def sample_raise_command() -> RaiseAlertFromScoreCommand:
    return RaiseAlertFromScoreCommand(
        transaction_id=uuid4(),
        scoring_result_id=uuid4(),
        account_id_hash="a" * 64,
        risk_score=78,
        level="HIGH",
        decision="REVIEW",
        model_version="xgb-prod-7",
        scored_at=datetime(2026, 11, 13, 13, 0, tzinfo=UTC),
        factors=[
            RiskFactor(
                feature="atypical_amount",
                weight=25.0,
                direction="increase",
                source="rule",
            ),
            RiskFactor(
                feature="amount_log",
                weight=0.3,
                direction="increase",
                source="shap",
            ),
        ],
    )
