from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from scoring.domain.model.aggregates.scoring_result import ScoringResult
from scoring.domain.model.events.scoring_result_registered_event import (
    ScoringResultRegisteredEvent,
)
from scoring.domain.model.valueobjects.decision import Decision
from scoring.domain.model.valueobjects.model_version import ModelVersion
from scoring.domain.model.valueobjects.risk_factor import RiskFactor
from scoring.domain.model.valueobjects.risk_score import RiskScore


def _register(score_value: float, degraded: bool = False) -> ScoringResult:
    return ScoringResult.register(
        transaction_id=uuid4(),
        account_id_hash="c" * 64,
        score=RiskScore(score_value),
        rules_score=int(score_value),
        xgb_probability=Decimal("0.30"),
        iforest_anomaly=Decimal("0.10"),
        model_version=ModelVersion("xgb-abc") if not degraded else ModelVersion.rules_only(),
        degraded_mode=degraded,
        factors=[
            RiskFactor(feature="amount_log", weight=0.2, direction="increase"),
        ],
        occurred_at=datetime(2026, 11, 13, tzinfo=UTC),
    )


def test_register_assigns_id_and_emits_event() -> None:
    result = _register(50.0)

    assert result.id is not None
    events = result.pull_events()
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, ScoringResultRegisteredEvent)
    assert event.scoring_result_id == result.id
    assert event.transaction_id == result.transaction_id
    assert event.score == 50
    assert event.level == "MEDIUM"
    assert event.decision == "REVIEW"
    assert event.degraded_mode is False
    assert event.model_version == "xgb-abc"


def test_register_block_decision_at_90() -> None:
    result = _register(90.0)
    assert result.decision is Decision.BLOCK
    assert result.level == "CRITICAL"


def test_register_approve_decision_at_0() -> None:
    result = _register(0.0)
    assert result.decision is Decision.APPROVE
    assert result.level == "LOW"


def test_pull_events_clears_buffer() -> None:
    result = _register(25.0)
    _ = result.pull_events()
    assert result.pull_events() == []


def test_restore_does_not_emit_event() -> None:
    result = ScoringResult.restore(
        id=uuid4(),
        transaction_id=uuid4(),
        account_id_hash="d" * 64,
        score=RiskScore(10.0),
        decision=Decision.APPROVE,
        level="LOW",
        rules_score=10,
        xgb_probability=Decimal("0.05"),
        iforest_anomaly=Decimal("0.02"),
        model_version=ModelVersion("xgb-v2"),
        degraded_mode=False,
        factors=[],
        occurred_at=datetime(2026, 11, 13, tzinfo=UTC),
    )
    assert result.pull_events() == []


def test_register_in_degraded_mode_uses_rules_only_version() -> None:
    result = _register(35.0, degraded=True)
    events = result.pull_events()
    assert events[0].degraded_mode is True
    assert events[0].model_version == "rules-only"
    assert result.model_version.value == "rules-only"
