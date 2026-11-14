from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

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
from analytics.infrastructure.persistence.repositories.analytics_projection_repository_impl import (
    AnalyticsProjectionRepositoryImpl,
)
from analytics.infrastructure.persistence.repositories.analytics_read_repository_impl import (
    AnalyticsReadRepositoryImpl,
)

pytestmark = pytest.mark.integration


async def _seed_transaction(
    repo: AnalyticsProjectionRepositoryImpl,
    *,
    occurred_at: datetime,
    country: str = "PE",
    decision: str = "REVIEW",
    score: int = 80,
) -> None:
    transaction_id = uuid4()
    await repo.upsert_transaction_received(
        transaction_id=transaction_id,
        account_id_hash="a" * 64,
        amount=Decimal("250.00"),
        currency="PEN",
        channel="WEB",
        country=country,
        device_id="d-1",
        occurred_at=occurred_at,
        received_at=occurred_at,
    )
    await repo.upsert_transaction_scored(
        transaction_id=transaction_id,
        account_id_hash="a" * 64,
        risk_score=score,
        level="HIGH" if score < 90 else "CRITICAL",
        decision=decision,
        model_version="xgb-v1",
        degraded_mode=False,
        scored_at=occurred_at,
    )


async def _seed_alert(
    repo: AnalyticsProjectionRepositoryImpl,
    *,
    opened_at: datetime,
    priority: str = "HIGH",
    status: str = "OPEN",
) -> None:
    alert_id = uuid4()
    await repo.upsert_alert_raised(
        alert_id=alert_id,
        transaction_id=uuid4(),
        account_id_hash="b" * 64,
        severity=priority,
        score=82,
        level=priority,
        opened_at=opened_at,
    )
    if status != "OPEN":
        await repo.upsert_alert_resolved(
            alert_id=alert_id,
            transaction_id=uuid4(),
            previous_status="IN_REVIEW",
            new_status=status,
            analyst_id=uuid4(),
            reason="done",
            closed_at=opened_at + timedelta(hours=1),
        )


@pytest.mark.asyncio
async def test_projection_received_then_scored_keeps_base_fields(session) -> None:
    async with session.begin():
        projection = AnalyticsProjectionRepositoryImpl(session)
        tx_id = uuid4()
        occurred = datetime(2026, 11, 14, 10, tzinfo=UTC)
        await projection.upsert_transaction_received(
            transaction_id=tx_id,
            account_id_hash="a" * 64,
            amount=Decimal("500.00"),
            currency="PEN",
            channel="WEB",
            country="PE",
            device_id="d-1",
            occurred_at=occurred,
            received_at=occurred,
        )
        await projection.upsert_transaction_scored(
            transaction_id=tx_id,
            account_id_hash="a" * 64,
            risk_score=92,
            level="CRITICAL",
            decision="BLOCK",
            model_version="xgb-v2",
            degraded_mode=False,
            scored_at=occurred + timedelta(seconds=30),
        )

    async with session.begin():
        read = AnalyticsReadRepositoryImpl(session)
        found = await read.list_transactions(
            ListTransactionsQuery(decision=Decision.BLOCK, limit=10)
        )

    assert len(found) == 1
    view = found[0]
    assert view.amount == Decimal("500.00")
    assert view.channel == "WEB"
    assert view.decision is Decision.BLOCK
    assert view.model_version == "xgb-v2"


@pytest.mark.asyncio
async def test_projection_scored_before_received_still_works(session) -> None:
    async with session.begin():
        projection = AnalyticsProjectionRepositoryImpl(session)
        tx_id = uuid4()
        when = datetime(2026, 11, 14, 11, tzinfo=UTC)
        # Out-of-order delivery.
        await projection.upsert_transaction_scored(
            transaction_id=tx_id,
            account_id_hash="a" * 64,
            risk_score=55,
            level="MEDIUM",
            decision="REVIEW",
            model_version="xgb-v1",
            degraded_mode=False,
            scored_at=when,
        )
        await projection.upsert_transaction_received(
            transaction_id=tx_id,
            account_id_hash="a" * 64,
            amount=Decimal("100.00"),
            currency="PEN",
            channel="MOBILE",
            country="PE",
            device_id=None,
            occurred_at=when - timedelta(seconds=10),
            received_at=when - timedelta(seconds=10),
        )

    async with session.begin():
        read = AnalyticsReadRepositoryImpl(session)
        rows = await read.list_transactions(ListTransactionsQuery(limit=10))

    assert len(rows) == 1
    assert rows[0].amount == Decimal("100.00")
    assert rows[0].risk_score == 55
    assert rows[0].decision is Decision.REVIEW


@pytest.mark.asyncio
async def test_list_transactions_filters_and_paginates(session) -> None:
    async with session.begin():
        projection = AnalyticsProjectionRepositoryImpl(session)
        base = datetime(2026, 11, 14, 12, tzinfo=UTC)
        for i in range(5):
            await _seed_transaction(
                projection,
                occurred_at=base + timedelta(minutes=i),
                country="PE",
                decision="BLOCK" if i % 2 == 0 else "REVIEW",
            )
        await _seed_transaction(
            projection, occurred_at=base, country="AR", decision="APPROVE", score=10
        )

    async with session.begin():
        read = AnalyticsReadRepositoryImpl(session)
        blocked = await read.list_transactions(
            ListTransactionsQuery(decision=Decision.BLOCK, limit=10)
        )
        from_pe = await read.list_transactions(
            ListTransactionsQuery(country="PE", limit=10)
        )
        page_1 = await read.list_transactions(ListTransactionsQuery(limit=2, offset=0))
        page_2 = await read.list_transactions(ListTransactionsQuery(limit=2, offset=2))

    assert len(blocked) == 3
    assert len(from_pe) == 5
    assert len(page_1) == 2 and len(page_2) == 2
    assert page_1[0].transaction_id != page_2[0].transaction_id


@pytest.mark.asyncio
async def test_list_alerts_filters_by_status_and_priority(session) -> None:
    async with session.begin():
        projection = AnalyticsProjectionRepositoryImpl(session)
        base = datetime(2026, 11, 14, 13, tzinfo=UTC)
        await _seed_alert(projection, opened_at=base, priority="HIGH", status="OPEN")
        await _seed_alert(
            projection, opened_at=base + timedelta(minutes=1), priority="CRITICAL", status="OPEN"
        )
        await _seed_alert(
            projection, opened_at=base + timedelta(minutes=2), priority="CRITICAL", status="RESOLVED"
        )

    async with session.begin():
        read = AnalyticsReadRepositoryImpl(session)
        criticals = await read.list_alerts(
            ListAlertsQuery(priority=Priority.CRITICAL, limit=10)
        )
        open_only = await read.list_alerts(
            ListAlertsQuery(status=AlertStatus.OPEN, limit=10)
        )

    assert len(criticals) == 2
    assert all(a.priority is Priority.CRITICAL for a in criticals)
    assert len(open_only) == 2
    assert all(a.status is AlertStatus.OPEN for a in open_only)


@pytest.mark.asyncio
async def test_daily_metrics_aggregate_tx_and_alerts(session) -> None:
    async with session.begin():
        projection = AnalyticsProjectionRepositoryImpl(session)
        day_one = datetime(2026, 11, 14, 12, tzinfo=UTC)
        day_two = datetime(2026, 11, 15, 12, tzinfo=UTC)
        for _ in range(3):
            await _seed_transaction(projection, occurred_at=day_one, decision="REVIEW")
        await _seed_transaction(projection, occurred_at=day_one, decision="BLOCK")
        await _seed_transaction(projection, occurred_at=day_two, decision="BLOCK")

        await _seed_alert(projection, opened_at=day_one, priority="CRITICAL")
        await _seed_alert(projection, opened_at=day_one, priority="HIGH")
        await _seed_alert(projection, opened_at=day_two, priority="LOW")

    async with session.begin():
        read = AnalyticsReadRepositoryImpl(session)
        metrics = await read.daily_metrics(
            GetDailyMetricsQuery(
                date_from=datetime(2026, 11, 14, tzinfo=UTC),
                date_to=datetime(2026, 11, 16, tzinfo=UTC),
            )
        )

    assert len(metrics) == 2
    by_day = {m.day: m for m in metrics}
    day_one_metric = by_day[day_one.date()]
    assert day_one_metric.transactions == 4
    assert day_one_metric.blocked == 1
    assert day_one_metric.alerts == 2
    assert day_one_metric.priority_critical == 1
    assert day_one_metric.priority_high == 1
    assert day_one_metric.fraud_rate == pytest.approx(2 / 4)


@pytest.mark.asyncio
async def test_summary_metrics_totals(session) -> None:
    async with session.begin():
        projection = AnalyticsProjectionRepositoryImpl(session)
        base = datetime(2026, 11, 16, 12, tzinfo=UTC)
        for _ in range(4):
            await _seed_transaction(projection, occurred_at=base, decision="REVIEW")
        await _seed_transaction(projection, occurred_at=base, decision="BLOCK")
        await _seed_transaction(projection, occurred_at=base, decision="APPROVE", score=5)
        await _seed_alert(projection, opened_at=base, status="OPEN")
        await _seed_alert(projection, opened_at=base, status="RESOLVED")

    async with session.begin():
        read = AnalyticsReadRepositoryImpl(session)
        summary = await read.summary_metrics(GetSummaryMetricsQuery())

    assert summary.total_transactions >= 6
    assert summary.blocked_transactions >= 1
    assert summary.review_transactions >= 4
    assert summary.total_alerts >= 2
    assert summary.resolved_alerts >= 1
