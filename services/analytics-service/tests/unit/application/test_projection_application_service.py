from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from analytics.application.dto.projection_input import (
    AlertRaisedInput,
    AlertResolvedInput,
    TransactionReceivedInput,
    TransactionScoredInput,
)
from analytics.application.internal.commandservices.projection_application_service_impl import (
    ProjectionApplicationServiceImpl,
)
from analytics.domain.model.valueobjects.alert_status import AlertStatus
from analytics.domain.model.valueobjects.decision import Decision
from analytics.domain.model.valueobjects.priority import Priority
from analytics.kernel.application.result import Failure, Success
from tests.unit.application.fakes.fake_processed_event_store import (
    FakeProcessedEventStore,
)
from tests.unit.application.fakes.fake_projection_repository import (
    FakeProjectionRepository,
)
from tests.unit.application.fakes.fake_session import (
    FakeSession,
    session_factory_with,
)

GROUP = "analytics.ingest-received"


def _service(
    *, repo: FakeProjectionRepository, store: FakeProcessedEventStore
) -> ProjectionApplicationServiceImpl:
    session = FakeSession()
    return ProjectionApplicationServiceImpl(
        session_factory=session_factory_with(session),
        projection_builder=lambda _s: repo,
        store_builder=lambda _s: store,
    )


def _received(transaction_id, message_id=None) -> TransactionReceivedInput:
    return TransactionReceivedInput(
        message_id=message_id or uuid4(),
        transaction_id=transaction_id,
        account_id_hash="a" * 64,
        amount=Decimal("250.00"),
        currency="PEN",
        channel="WEB",
        country="PE",
        device_id="d-1",
        occurred_at=datetime(2026, 11, 14, 13, 0, tzinfo=UTC),
        received_at=datetime(2026, 11, 14, 13, 0, 5, tzinfo=UTC),
    )


def _scored(transaction_id, message_id=None) -> TransactionScoredInput:
    return TransactionScoredInput(
        message_id=message_id or uuid4(),
        transaction_id=transaction_id,
        account_id_hash="a" * 64,
        risk_score=82,
        level="HIGH",
        decision="REVIEW",
        model_version="xgb-v1",
        degraded_mode=False,
        scored_at=datetime(2026, 11, 14, 13, 0, 10, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_on_transaction_received_upserts_view() -> None:
    repo = FakeProjectionRepository()
    store = FakeProcessedEventStore()
    service = _service(repo=repo, store=store)
    tx_id = uuid4()
    input_ = _received(tx_id)

    result = await service.on_transaction_received(input_, GROUP)

    assert isinstance(result, Success)
    assert tx_id in repo.transactions
    assert (input_.message_id, GROUP) in store.markers


@pytest.mark.asyncio
async def test_duplicate_delivery_is_noop() -> None:
    repo = FakeProjectionRepository()
    store = FakeProcessedEventStore()
    service = _service(repo=repo, store=store)
    message_id = uuid4()
    input_ = _received(uuid4(), message_id=message_id)

    first = await service.on_transaction_received(input_, GROUP)
    before = dict(repo.transactions)

    second = await service.on_transaction_received(input_, GROUP)

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    # Second call sees the marker and skips the upsert entirely.
    assert repo.transactions == before


@pytest.mark.asyncio
async def test_scored_after_received_fills_scoring_fields() -> None:
    repo = FakeProjectionRepository()
    store = FakeProcessedEventStore()
    service = _service(repo=repo, store=store)
    tx_id = uuid4()

    await service.on_transaction_received(_received(tx_id), GROUP)
    await service.on_transaction_scored(_scored(tx_id), "analytics.ingest-scored")

    view = repo.transactions[tx_id]
    assert view.risk_score == 82
    assert view.decision is Decision.REVIEW
    assert view.model_version == "xgb-v1"
    # And the received fields are still there.
    assert view.amount == Decimal("250.00")


@pytest.mark.asyncio
async def test_alert_raised_then_resolved() -> None:
    repo = FakeProjectionRepository()
    store = FakeProcessedEventStore()
    service = _service(repo=repo, store=store)
    alert_id = uuid4()
    tx_id = uuid4()

    await service.on_alert_raised(
        AlertRaisedInput(
            message_id=uuid4(),
            alert_id=alert_id,
            transaction_id=tx_id,
            account_id_hash="b" * 64,
            severity="HIGH",
            score=82,
            level="HIGH",
            opened_at=datetime(2026, 11, 14, 13, 0, tzinfo=UTC),
        ),
        "analytics.ingest-alerts",
    )

    assert repo.alerts[alert_id].status is AlertStatus.OPEN
    assert repo.alerts[alert_id].priority is Priority.HIGH

    analyst = uuid4()
    await service.on_alert_resolved(
        AlertResolvedInput(
            message_id=uuid4(),
            alert_id=alert_id,
            transaction_id=tx_id,
            previous_status="IN_REVIEW",
            new_status="RESOLVED",
            analyst_id=analyst,
            reason="confirmed",
            closed_at=datetime(2026, 11, 14, 14, 0, tzinfo=UTC),
        ),
        "analytics.ingest-alerts",
    )

    final = repo.alerts[alert_id]
    assert final.status is AlertStatus.RESOLVED
    assert final.analyst_id == analyst
    assert final.resolution == "confirmed"


@pytest.mark.asyncio
async def test_failure_in_repo_returns_failure() -> None:
    class FailingRepo(FakeProjectionRepository):
        async def upsert_transaction_received(self, **kwargs):  # type: ignore[override]
            raise RuntimeError("db-down")

    service = _service(repo=FailingRepo(), store=FakeProcessedEventStore())

    result = await service.on_transaction_received(_received(uuid4()), GROUP)

    assert isinstance(result, Failure)
    assert result.error.code == "unexpected"
