from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from alert.application.internal.eventhandlers.alert_raised_event_handler import (
    AlertRaisedEventHandler,
)
from alert.application.internal.eventhandlers.alert_resolved_event_handler import (
    AlertResolvedEventHandler,
)
from alert.domain.model.aggregates.alert import Alert
from alert.domain.model.commands.raise_alert_from_score_command import (
    RaiseAlertFromScoreCommand,
)
from alert.domain.model.events.alert_raised_event import AlertRaisedEvent
from alert.domain.model.events.alert_resolved_event import AlertResolvedEvent
from alert.domain.model.queries.list_alerts_query import ListAlertsQuery
from alert.domain.model.valueobjects.alert_status import AlertStatus
from alert.domain.model.valueobjects.priority import Priority
from alert.infrastructure.messaging.outbox.outbox_message_publisher import (
    OutboxMessagePublisher,
)
from alert.infrastructure.messaging.outbox.outbox_persistence_entity import (
    OutboxPersistenceEntity,
)
from alert.infrastructure.persistence.repositories.alert_repository_impl import (
    AlertRepositoryImpl,
)
from alert.kernel.domain.event_dispatcher import EventDispatcher

pytestmark = pytest.mark.integration


def _build_repo(session) -> AlertRepositoryImpl:
    publisher = OutboxMessagePublisher(session)
    raised = AlertRaisedEventHandler(publisher)
    resolved = AlertResolvedEventHandler(publisher)
    dispatcher = EventDispatcher()
    dispatcher.register(AlertRaisedEvent, raised.on_alert_raised)
    dispatcher.register(AlertResolvedEvent, resolved.on_alert_resolved)
    return AlertRepositoryImpl(session, dispatcher)


def _sample_command(
    *, risk_score: int = 78, decision: str = "REVIEW"
) -> RaiseAlertFromScoreCommand:
    return RaiseAlertFromScoreCommand(
        transaction_id=uuid4(),
        scoring_result_id=uuid4(),
        account_id_hash="a" * 64,
        risk_score=risk_score,
        level="HIGH",
        decision=decision,
        model_version="xgb-prod-7",
        scored_at=datetime(2026, 11, 13, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_save_and_find_by_id(session) -> None:
    repo = _build_repo(session)
    alert = Alert.register(_sample_command())

    async with session.begin():
        await repo.save(alert)

    async with session.begin():
        found = await repo.find_by_id(alert.id)

    assert found is not None
    assert found.status is AlertStatus.OPEN
    assert found.priority is Priority.HIGH


@pytest.mark.asyncio
async def test_find_by_transaction_id(session) -> None:
    repo = _build_repo(session)
    alert = Alert.register(_sample_command())

    async with session.begin():
        await repo.save(alert)

    async with session.begin():
        found = await repo.find_by_transaction_id(alert.transaction_id)

    assert found is not None
    assert found.id == alert.id


@pytest.mark.asyncio
async def test_save_writes_alert_raised_outbox_row(session) -> None:
    repo = _build_repo(session)
    alert = Alert.register(_sample_command())

    async with session.begin():
        await repo.save(alert)

    rows = (
        await session.execute(
            select(OutboxPersistenceEntity).where(
                OutboxPersistenceEntity.channel == "alerts.raised.v1"
            )
        )
    ).scalars().all()
    assert len(rows) >= 1
    row = rows[-1]
    assert row.message_type == "AlertRaised"
    assert row.status == "PENDING"
    assert row.payload["payload"]["severity"] == "HIGH"


@pytest.mark.asyncio
async def test_upsert_allows_status_transitions(session) -> None:
    repo = _build_repo(session)
    alert = Alert.register(_sample_command())
    analyst = uuid4()

    async with session.begin():
        await repo.save(alert)

    alert.assign(analyst)
    async with session.begin():
        await repo.save(alert)

    alert.resolve("confirmed")
    async with session.begin():
        await repo.save(alert)

    async with session.begin():
        found = await repo.find_by_id(alert.id)

    assert found is not None
    assert found.status is AlertStatus.RESOLVED
    assert found.analyst_id == analyst
    assert found.resolution == "confirmed"

    rows = (
        await session.execute(
            select(OutboxPersistenceEntity).where(
                OutboxPersistenceEntity.channel == "alerts.resolved.v1"
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].payload["payload"]["new_status"] == "RESOLVED"


@pytest.mark.asyncio
async def test_list_by_filters_and_paginates(session) -> None:
    repo = _build_repo(session)

    async with session.begin():
        await repo.save(Alert.register(_sample_command(risk_score=55)))  # MEDIUM
        await repo.save(Alert.register(_sample_command(risk_score=92)))  # CRITICAL
        await repo.save(Alert.register(_sample_command(risk_score=95)))  # CRITICAL

    async with session.begin():
        criticals = await repo.list_by(
            ListAlertsQuery(priority=Priority.CRITICAL, limit=50, offset=0)
        )

    assert len(criticals) == 2
    for a in criticals:
        assert a.priority is Priority.CRITICAL

    async with session.begin():
        open_only = await repo.list_by(
            ListAlertsQuery(status=AlertStatus.OPEN, limit=1, offset=0)
        )
    assert len(open_only) == 1
