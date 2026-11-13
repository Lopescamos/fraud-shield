from __future__ import annotations

import pytest

from scoring.domain.model.valueobjects.decision import Decision, level_from_score
from scoring.domain.model.valueobjects.model_version import ModelVersion
from scoring.domain.model.valueobjects.risk_factor import RiskFactor
from scoring.domain.model.valueobjects.risk_score import RiskScore


@pytest.mark.parametrize("value", [0.0, 50.5, 100.0])
def test_risk_score_accepts_valid_range(value: float) -> None:
    assert RiskScore(value).value == value


@pytest.mark.parametrize("value", [-0.1, 100.01, 200.0])
def test_risk_score_rejects_out_of_range(value: float) -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        RiskScore(value)


@pytest.mark.parametrize("value, expected", [(10.4, 10), (10.6, 11), (0.5, 0)])
def test_risk_score_as_int_rounds(value: float, expected: int) -> None:
    assert RiskScore(value).as_int() == expected


@pytest.mark.parametrize(
    "score, decision",
    [(0, Decision.APPROVE), (39, Decision.APPROVE), (40, Decision.REVIEW),
     (89, Decision.REVIEW), (90, Decision.BLOCK), (100, Decision.BLOCK)],
)
def test_decision_from_score_uses_adr007_thresholds(
    score: int, decision: Decision
) -> None:
    assert Decision.from_score(score) is decision


def test_decision_rejects_invalid_score() -> None:
    with pytest.raises(ValueError):
        Decision.from_score(-1)
    with pytest.raises(ValueError):
        Decision.from_score(101)


@pytest.mark.parametrize(
    "score, level",
    [(0, "LOW"), (39, "LOW"), (40, "MEDIUM"), (69, "MEDIUM"),
     (70, "HIGH"), (89, "HIGH"), (90, "CRITICAL"), (100, "CRITICAL")],
)
def test_level_from_score_matches_adr007(score: int, level: str) -> None:
    assert level_from_score(score) == level


def test_model_version_rejects_empty() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        ModelVersion("   ")


def test_model_version_rules_only_factory() -> None:
    assert ModelVersion.rules_only().value == "rules-only"


def test_risk_factor_validates_direction() -> None:
    with pytest.raises(ValueError, match="direction"):
        RiskFactor(feature="amount", weight=0.1, direction="unknown")


def test_risk_factor_validates_source() -> None:
    with pytest.raises(ValueError, match="source"):
        RiskFactor(feature="amount", weight=0.1, direction="increase", source="bogus")


def test_risk_factor_rejects_empty_feature() -> None:
    with pytest.raises(ValueError, match="feature"):
        RiskFactor(feature="   ", weight=0.1, direction="increase")
