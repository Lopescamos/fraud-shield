from __future__ import annotations

import pytest

from scoring.application.internal.commandservices.scoring_application_service_impl import (
    ScoringApplicationServiceImpl,
    ScoringWeights,
)
from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.domain.model.valueobjects.risk_factor import RiskFactor
from scoring.kernel.application.result import Failure, Success

from tests.unit.application.fakes.fake_ports import (
    FailingRuleEngine,
    StaticExplainer,
    StaticRiskModel,
    StaticRuleEngine,
    ThrowingRiskModel,
)
from tests.unit.application.fakes.fake_scoring_result_repository import (
    FakeScoringResultRepository,
)
from tests.unit.application.fakes.fake_session import (
    FakeSession,
    repo_builder,
    session_factory_with,
)


def _build_service(
    *,
    repo: FakeScoringResultRepository,
    session: FakeSession,
    rule_engine=None,
    xgb=None,
    iforest=None,
    explainer=None,
) -> ScoringApplicationServiceImpl:
    return ScoringApplicationServiceImpl(
        session_factory=session_factory_with(session),
        repository_builder=repo_builder(repo),
        rule_engine=rule_engine or StaticRuleEngine(score=10, factors=[]),
        xgb_model=xgb or StaticRiskModel(available=False),
        iforest_model=iforest or StaticRiskModel(available=False),
        explainer=explainer or StaticExplainer(available=False),
        weights=ScoringWeights(rules=0.4, xgb=0.4, iforest=0.2),
    )


@pytest.mark.asyncio
async def test_degrades_to_rules_only_when_models_unavailable(
    sample_score_command: ScoreTransactionCommand,
) -> None:
    repo = FakeScoringResultRepository()
    session = FakeSession()
    service = _build_service(
        repo=repo,
        session=session,
        rule_engine=StaticRuleEngine(
            score=50,
            factors=[
                RiskFactor(
                    feature="atypical_amount",
                    weight=25,
                    direction="increase",
                    source="rule",
                )
            ],
        ),
    )

    result = await service.handle(sample_score_command)

    assert isinstance(result, Success)
    assert len(repo.published_events) == 1
    event = repo.published_events[0]
    assert event.degraded_mode is True
    assert event.model_version == "rules-only"
    # Only rules contribute: 0.4 * 50 = 20
    assert event.score == 20
    assert event.decision == "APPROVE"


@pytest.mark.asyncio
async def test_combines_rules_xgb_iforest_when_all_available(
    sample_score_command: ScoreTransactionCommand,
) -> None:
    repo = FakeScoringResultRepository()
    session = FakeSession()
    service = _build_service(
        repo=repo,
        session=session,
        rule_engine=StaticRuleEngine(score=50, factors=[]),
        xgb=StaticRiskModel(available=True, score=0.8, version="xgb-prod-1"),
        iforest=StaticRiskModel(available=True, score=0.5),
        explainer=StaticExplainer(
            available=True,
            factors=[
                RiskFactor(feature="amount_log", weight=0.3, direction="increase"),
                RiskFactor(feature="new_device", weight=0.2, direction="increase"),
                RiskFactor(feature="hour_of_day", weight=-0.1, direction="decrease"),
            ],
        ),
    )

    result = await service.handle(sample_score_command)

    assert isinstance(result, Success)
    event = repo.published_events[0]
    # 0.4 * 50 + 0.4 * 100 * 0.8 + 0.2 * 100 * 0.5 = 20 + 32 + 10 = 62
    assert event.score == 62
    assert event.level == "MEDIUM"
    assert event.decision == "REVIEW"
    assert event.degraded_mode is False
    assert event.model_version == "xgb-prod-1"


@pytest.mark.asyncio
async def test_is_idempotent_by_transaction_id(
    sample_score_command: ScoreTransactionCommand,
) -> None:
    repo = FakeScoringResultRepository()

    service1 = _build_service(repo=repo, session=FakeSession())
    first = await service1.handle(sample_score_command)
    assert isinstance(first, Success)

    service2 = _build_service(repo=repo, session=FakeSession())
    second = await service2.handle(sample_score_command)
    assert isinstance(second, Success)
    assert second.value == first.value
    assert len(repo.published_events) == 1


@pytest.mark.asyncio
async def test_rolls_back_when_rules_engine_fails(
    sample_score_command: ScoreTransactionCommand,
) -> None:
    repo = FakeScoringResultRepository()
    session = FakeSession()
    service = _build_service(
        repo=repo,
        session=session,
        rule_engine=FailingRuleEngine(),
    )

    result = await service.handle(sample_score_command)

    assert isinstance(result, Failure)
    assert result.error.code == "unexpected"
    assert session.trans.rolled_back is True
    assert repo.published_events == []


@pytest.mark.asyncio
async def test_degrades_when_xgb_scoring_throws(
    sample_score_command: ScoreTransactionCommand,
) -> None:
    repo = FakeScoringResultRepository()
    session = FakeSession()
    service = _build_service(
        repo=repo,
        session=session,
        rule_engine=StaticRuleEngine(score=25),
        xgb=ThrowingRiskModel(),
        iforest=StaticRiskModel(available=True, score=0.1),
    )

    result = await service.handle(sample_score_command)

    assert isinstance(result, Success)
    event = repo.published_events[0]
    assert event.degraded_mode is True
    # rules only: 0.4 * 25 + 0.2 * 100 * 0.1 = 10 + 2 = 12
    assert event.score == 12
    assert event.model_version == "rules-only"


@pytest.mark.asyncio
async def test_does_not_call_explainer_in_degraded_mode(
    sample_score_command: ScoreTransactionCommand,
) -> None:
    repo = FakeScoringResultRepository()
    session = FakeSession()
    explainer = StaticExplainer(available=True, factors=[
        RiskFactor(feature="amount_log", weight=0.1, direction="increase"),
    ])
    service = _build_service(
        repo=repo,
        session=session,
        rule_engine=StaticRuleEngine(score=20),
        xgb=StaticRiskModel(available=False),
        iforest=StaticRiskModel(available=True, score=0.3),
        explainer=explainer,
    )

    result = await service.handle(sample_score_command)

    assert isinstance(result, Success)
    assert explainer.calls == 0


@pytest.mark.asyncio
async def test_rolls_back_when_repository_save_fails(
    sample_score_command: ScoreTransactionCommand,
) -> None:
    class FailingRepo(FakeScoringResultRepository):
        async def save(self, result):  # type: ignore[override]
            raise RuntimeError("db-down")

    session = FakeSession()
    service = _build_service(
        repo=FailingRepo(),
        session=session,
    )

    result = await service.handle(sample_score_command)

    assert isinstance(result, Failure)
    assert result.error.code == "unexpected"
    assert session.trans.rolled_back is True
