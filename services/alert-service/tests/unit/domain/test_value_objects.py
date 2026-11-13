from __future__ import annotations

from uuid import uuid4

import pytest

from alert.domain.model.valueobjects.alert_id import AlertId
from alert.domain.model.valueobjects.alert_status import AlertStatus
from alert.domain.model.valueobjects.priority import Priority
from alert.domain.model.valueobjects.risk_factor import RiskFactor


@pytest.mark.parametrize(
    "score, priority",
    [
        (0, Priority.LOW),
        (49, Priority.LOW),
        (50, Priority.MEDIUM),
        (74, Priority.MEDIUM),
        (75, Priority.HIGH),
        (89, Priority.HIGH),
        (90, Priority.CRITICAL),
        (100, Priority.CRITICAL),
    ],
)
def test_priority_from_risk_score_uses_documented_thresholds(
    score: int, priority: Priority
) -> None:
    assert Priority.from_risk_score(score) is priority


@pytest.mark.parametrize("score", [-1, 101, 200])
def test_priority_rejects_out_of_range(score: int) -> None:
    with pytest.raises(ValueError, match="0..100"):
        Priority.from_risk_score(score)


def test_alert_id_wraps_uuid() -> None:
    uid = uuid4()
    assert AlertId(uid).value == uid


def test_alert_id_rejects_non_uuid() -> None:
    with pytest.raises(ValueError, match="UUID"):
        AlertId("not-a-uuid")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "status, terminal",
    [
        (AlertStatus.OPEN, False),
        (AlertStatus.IN_REVIEW, False),
        (AlertStatus.RESOLVED, True),
        (AlertStatus.DISMISSED, True),
    ],
)
def test_alert_status_terminal_flag(status: AlertStatus, terminal: bool) -> None:
    assert status.is_terminal() is terminal


def test_risk_factor_validates_direction() -> None:
    with pytest.raises(ValueError, match="direction"):
        RiskFactor(feature="amount", weight=0.1, direction="unknown")


def test_risk_factor_validates_source() -> None:
    with pytest.raises(ValueError, match="source"):
        RiskFactor(feature="amount", weight=0.1, direction="increase", source="bogus")


def test_risk_factor_rejects_empty_feature() -> None:
    with pytest.raises(ValueError, match="feature"):
        RiskFactor(feature="   ", weight=0.1, direction="increase")
