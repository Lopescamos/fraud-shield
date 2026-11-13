from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from scoring.application.internal.eventhandlers.scoring_result_registered_event_handler import (
    ScoringResultRegisteredEventHandler,
)
from scoring.domain.model.aggregates.scoring_result import ScoringResult
from scoring.domain.model.events.scoring_result_registered_event import (
    ScoringResultRegisteredEvent,
)
from scoring.domain.model.valueobjects.model_version import ModelVersion
from scoring.domain.model.valueobjects.risk_factor import RiskFactor
from scoring.domain.model.valueobjects.risk_score import RiskScore
from scoring.infrastructure.messaging.outbox.outbox_message_publisher import (
    OutboxMessagePublisher,
)
from scoring.infrastructure.messaging.outbox.outbox_persistence_entity import (
    OutboxPersistenceEntity,
)
from scoring.infrastructure.persistence.repositories.scoring_result_repository_impl import (
    ScoringResultRepositoryImpl,
)
from scoring.kernel.domain.event_dispatcher import EventDispatcher

pytestmark = pytest.mark.integration


def _build_repo(session) -> ScoringResultRepositoryImpl:
    publisher = OutboxMessagePublisher(session)
    handler = ScoringResultRegisteredEventHandler(publisher)
    dispatcher = EventDispatcher()
    dispatcher.register(
        ScoringResultRegisteredEvent, handler.on_scoring_result_registered
    )
    return ScoringResultRepositoryImpl(session, dispatcher)


def _sample_aggregate() -> ScoringResult:
    return ScoringResult.register(
        transaction_id=uuid4(),
        account_id_hash="c" * 64,
        score=RiskScore(55.0),
        rules_score=30,
        xgb_probability=Decimal("0.60"),
        iforest_anomaly=Decimal("0.20"),
        model_version=ModelVersion("xgb-prod-42"),
        degraded_mode=False,
        factors=[
            RiskFactor(feature="amount_log", weight=0.3, direction="increase"),
            RiskFactor(feature="hour_of_day", weight=-0.1, direction="decrease"),
        ],
        occurred_at=datetime(2026, 11, 13, 10, 0, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_save_and_find_by_id(session) -> None:
    repo = _build_repo(session)
    aggregate = _sample_aggregate()

    async with session.begin():
        saved = await repo.save(aggregate)

    async with session.begin():
        found = await repo.find_by_id(saved.id)

    assert found is not None
    assert found.score.as_int() == 55
    assert found.decision.value == "REVIEW"
    assert found.model_version.value == "xgb-prod-42"
    assert len(found.factors) == 2


@pytest.mark.asyncio
async def test_find_by_transaction_id_returns_existing(session) -> None:
    repo = _build_repo(session)
    aggregate = _sample_aggregate()

    async with session.begin():
        saved = await repo.save(aggregate)

    async with session.begin():
        found = await repo.find_by_transaction_id(saved.transaction_id)

    assert found is not None
    assert found.id == saved.id


@pytest.mark.asyncio
async def test_save_writes_outbox_row_with_scored_envelope(session) -> None:
    repo = _build_repo(session)

    async with session.begin():
        await repo.save(_sample_aggregate())

    rows = (
        await session.execute(
            select(OutboxPersistenceEntity).where(
                OutboxPersistenceEntity.channel == "transactions.scored.v1"
            )
        )
    ).scalars().all()
    assert len(rows) >= 1
    row = rows[-1]
    assert row.message_type == "TransactionScored"
    assert row.status == "PENDING"
    assert row.payload["payload"]["level"] == "MEDIUM"
    assert row.payload["payload"]["decision"] == "REVIEW"


@pytest.mark.asyncio
async def test_transaction_id_unique_constraint_prevents_duplicates(session) -> None:
    repo = _build_repo(session)
    first = _sample_aggregate()

    async with session.begin():
        await repo.save(first)

    duplicate = ScoringResult.register(
        transaction_id=first.transaction_id,
        account_id_hash=first.account_id_hash,
        score=RiskScore(90.0),
        rules_score=50,
        xgb_probability=Decimal("0.90"),
        iforest_anomaly=Decimal("0.80"),
        model_version=ModelVersion("other-model"),
        degraded_mode=False,
        factors=[],
        occurred_at=datetime(2026, 11, 13, 11, 0, tzinfo=UTC),
    )

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        async with session.begin():
            await repo.save(duplicate)
