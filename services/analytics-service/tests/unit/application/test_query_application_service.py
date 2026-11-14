from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from analytics.application.internal.queryservices.query_application_service_impl import (
    QueryApplicationServiceImpl,
)
from analytics.domain.model.queries.daily_metrics_query import (
    GetDailyMetricsQuery,
    GetSummaryMetricsQuery,
)
from analytics.domain.model.queries.list_alerts_query import ListAlertsQuery
from analytics.domain.model.queries.list_transactions_query import (
    ListTransactionsQuery,
)
from analytics.domain.model.valueobjects.alert_status import AlertStatus
from analytics.domain.model.valueobjects.decision import Decision
from analytics.domain.model.valueobjects.priority import Priority
from analytics.domain.model.views.alert_view import AlertView
from analytics.domain.model.views.metrics_views import DailyMetric, SummaryMetric
from analytics.domain.model.views.transaction_view import TransactionView
from tests.unit.application.fakes.fake_read_repository import FakeReadRepository
from tests.unit.application.fakes.fake_session import (
    FakeSession,
    session_factory_with,
)


def _service(repo: FakeReadRepository) -> QueryApplicationServiceImpl:
    return QueryApplicationServiceImpl(
        session_factory=session_factory_with(FakeSession()),
        read_builder=lambda _s: repo,
    )


def _tx_view() -> TransactionView:
    return TransactionView(
        transaction_id=uuid4(),
        account_id_hash="a" * 64,
        amount=Decimal("250.00"),
        currency="PEN",
        channel="WEB",
        country="PE",
        device_id="d-1",
        occurred_at=datetime(2026, 11, 14, 13, tzinfo=UTC),
        received_at=datetime(2026, 11, 14, 13, tzinfo=UTC),
        risk_score=82,
        level="HIGH",
        decision=Decision.REVIEW,
        model_version="xgb-v1",
        degraded_mode=False,
        scored_at=datetime(2026, 11, 14, 13, 1, tzinfo=UTC),
    )


def _alert_view() -> AlertView:
    return AlertView(
        alert_id=uuid4(),
        transaction_id=uuid4(),
        account_id_hash="b" * 64,
        priority=Priority.CRITICAL,
        score=95,
        level="CRITICAL",
        status=AlertStatus.OPEN,
        opened_at=datetime(2026, 11, 14, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_list_transactions_maps_to_flat_dtos() -> None:
    view = _tx_view()
    service = _service(FakeReadRepository(transactions=[view]))

    dtos = await service.list_transactions(ListTransactionsQuery(limit=10))

    assert len(dtos) == 1
    dto = dtos[0]
    assert dto.transaction_id == view.transaction_id
    assert dto.decision == "REVIEW"  # Decision enum -> plain string
    assert dto.risk_score == 82


@pytest.mark.asyncio
async def test_list_transactions_forwards_filters_to_repo() -> None:
    repo = FakeReadRepository()
    service = _service(repo)
    q = ListTransactionsQuery(
        date_from=datetime(2026, 11, 1, tzinfo=UTC),
        date_to=datetime(2026, 11, 14, tzinfo=UTC),
        decision=Decision.BLOCK,
        country="PE",
        limit=25,
        offset=50,
    )

    await service.list_transactions(q)

    assert repo.last_transactions_query == q


@pytest.mark.asyncio
async def test_list_alerts_maps_enums_to_strings() -> None:
    view = _alert_view()
    service = _service(FakeReadRepository(alerts=[view]))

    dtos = await service.list_alerts(ListAlertsQuery(limit=10))

    assert dtos[0].priority == "CRITICAL"
    assert dtos[0].status == "OPEN"


@pytest.mark.asyncio
async def test_daily_metrics_pass_through() -> None:
    metric = DailyMetric(
        day=datetime(2026, 11, 14).date(),
        transactions=100,
        alerts=10,
        blocked=2,
        fraud_rate=0.1,
        priority_low=5,
        priority_medium=3,
        priority_high=1,
        priority_critical=1,
    )
    service = _service(FakeReadRepository(daily=[metric]))

    dtos = await service.daily_metrics(
        GetDailyMetricsQuery(
            date_from=datetime(2026, 11, 1, tzinfo=UTC),
            date_to=datetime(2026, 11, 14, tzinfo=UTC),
        )
    )

    assert dtos[0].transactions == 100
    assert dtos[0].priority_critical == 1


@pytest.mark.asyncio
async def test_summary_metrics_pass_through() -> None:
    summary = SummaryMetric(
        total_transactions=1_000,
        total_alerts=50,
        open_alerts=10,
        in_review_alerts=5,
        resolved_alerts=25,
        dismissed_alerts=10,
        blocked_transactions=20,
        review_transactions=30,
        fraud_rate=0.05,
    )
    service = _service(FakeReadRepository(summary=summary))

    dto = await service.summary_metrics(GetSummaryMetricsQuery())

    assert dto.total_alerts == 50
    assert dto.fraud_rate == 0.05
