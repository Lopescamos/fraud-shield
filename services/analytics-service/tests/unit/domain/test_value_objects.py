from __future__ import annotations

import pytest

from analytics.domain.model.valueobjects.alert_status import AlertStatus
from analytics.domain.model.valueobjects.decision import Decision
from analytics.domain.model.valueobjects.priority import Priority
from analytics.domain.model.valueobjects.risk_score import RiskScore


@pytest.mark.parametrize("value", [0, 50, 100])
def test_risk_score_accepts_valid_range(value: int) -> None:
    assert RiskScore(value).value == value


@pytest.mark.parametrize("value", [-1, 101, 200])
def test_risk_score_rejects_out_of_range(value: int) -> None:
    with pytest.raises(ValueError, match="0..100"):
        RiskScore(value)


def test_decision_values_are_stable() -> None:
    assert {d.value for d in Decision} == {"APPROVE", "REVIEW", "BLOCK"}


def test_alert_status_values_are_stable() -> None:
    assert {s.value for s in AlertStatus} == {
        "OPEN",
        "IN_REVIEW",
        "RESOLVED",
        "DISMISSED",
    }


def test_priority_values_are_stable() -> None:
    assert {p.value for p in Priority} == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
