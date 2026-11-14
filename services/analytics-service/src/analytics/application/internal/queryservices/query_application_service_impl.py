from __future__ import annotations

from collections.abc import Callable
from typing import Any

from analytics.application.dto.read_dtos import (
    AlertDTO,
    DailyMetricDTO,
    SummaryMetricDTO,
    TransactionDTO,
)
from analytics.domain.model.queries.daily_metrics_query import (
    GetDailyMetricsQuery,
    GetSummaryMetricsQuery,
)
from analytics.domain.model.queries.list_alerts_query import ListAlertsQuery
from analytics.domain.model.queries.list_transactions_query import (
    ListTransactionsQuery,
)
from analytics.domain.model.views.alert_view import AlertView
from analytics.domain.model.views.metrics_views import DailyMetric, SummaryMetric
from analytics.domain.model.views.transaction_view import TransactionView
from analytics.domain.repositories.analytics_read_repository import (
    AnalyticsReadRepository,
)

ReadBuilder = Callable[[Any], AnalyticsReadRepository]


class QueryApplicationServiceImpl:
    def __init__(
        self,
        session_factory: Any,
        read_builder: ReadBuilder,
    ) -> None:
        self._session_factory = session_factory
        self._read_builder = read_builder

    async def list_transactions(
        self, query: ListTransactionsQuery
    ) -> list[TransactionDTO]:
        async with self._session_factory() as session:
            repo = self._read_builder(session)
            views = await repo.list_transactions(query)
            return [_tx_to_dto(v) for v in views]

    async def list_alerts(self, query: ListAlertsQuery) -> list[AlertDTO]:
        async with self._session_factory() as session:
            repo = self._read_builder(session)
            views = await repo.list_alerts(query)
            return [_alert_to_dto(v) for v in views]

    async def daily_metrics(
        self, query: GetDailyMetricsQuery
    ) -> list[DailyMetricDTO]:
        async with self._session_factory() as session:
            repo = self._read_builder(session)
            metrics = await repo.daily_metrics(query)
            return [_daily_to_dto(m) for m in metrics]

    async def summary_metrics(
        self, query: GetSummaryMetricsQuery
    ) -> SummaryMetricDTO:
        async with self._session_factory() as session:
            repo = self._read_builder(session)
            summary = await repo.summary_metrics(query)
            return _summary_to_dto(summary)


def _tx_to_dto(view: TransactionView) -> TransactionDTO:
    return TransactionDTO(
        transaction_id=view.transaction_id,
        account_id_hash=view.account_id_hash,
        amount=view.amount,
        currency=view.currency,
        channel=view.channel,
        country=view.country,
        device_id=view.device_id,
        occurred_at=view.occurred_at,
        received_at=view.received_at,
        risk_score=view.risk_score,
        level=view.level,
        decision=view.decision.value if view.decision is not None else None,
        model_version=view.model_version,
        degraded_mode=view.degraded_mode,
        scored_at=view.scored_at,
    )


def _alert_to_dto(view: AlertView) -> AlertDTO:
    return AlertDTO(
        alert_id=view.alert_id,
        transaction_id=view.transaction_id,
        account_id_hash=view.account_id_hash,
        priority=view.priority.value,
        score=view.score,
        level=view.level,
        status=view.status.value,
        opened_at=view.opened_at,
        analyst_id=view.analyst_id,
        resolution=view.resolution,
        closed_at=view.closed_at,
    )


def _daily_to_dto(m: DailyMetric) -> DailyMetricDTO:
    return DailyMetricDTO(
        day=m.day,
        transactions=m.transactions,
        alerts=m.alerts,
        blocked=m.blocked,
        fraud_rate=m.fraud_rate,
        priority_low=m.priority_low,
        priority_medium=m.priority_medium,
        priority_high=m.priority_high,
        priority_critical=m.priority_critical,
    )


def _summary_to_dto(s: SummaryMetric) -> SummaryMetricDTO:
    return SummaryMetricDTO(
        total_transactions=s.total_transactions,
        total_alerts=s.total_alerts,
        open_alerts=s.open_alerts,
        in_review_alerts=s.in_review_alerts,
        resolved_alerts=s.resolved_alerts,
        dismissed_alerts=s.dismissed_alerts,
        blocked_transactions=s.blocked_transactions,
        review_transactions=s.review_transactions,
        fraud_rate=s.fraud_rate,
    )
