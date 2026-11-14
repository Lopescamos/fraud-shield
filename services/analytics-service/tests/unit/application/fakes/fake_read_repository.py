from __future__ import annotations

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


class FakeReadRepository:
    def __init__(
        self,
        *,
        transactions: list[TransactionView] | None = None,
        alerts: list[AlertView] | None = None,
        daily: list[DailyMetric] | None = None,
        summary: SummaryMetric | None = None,
    ) -> None:
        self._transactions = list(transactions or [])
        self._alerts = list(alerts or [])
        self._daily = list(daily or [])
        self._summary = summary or SummaryMetric(
            total_transactions=0,
            total_alerts=0,
            open_alerts=0,
            in_review_alerts=0,
            resolved_alerts=0,
            dismissed_alerts=0,
            blocked_transactions=0,
            review_transactions=0,
            fraud_rate=0.0,
        )
        self.last_transactions_query: ListTransactionsQuery | None = None
        self.last_alerts_query: ListAlertsQuery | None = None

    async def list_transactions(
        self, query: ListTransactionsQuery
    ) -> list[TransactionView]:
        self.last_transactions_query = query
        return self._transactions[query.offset : query.offset + query.limit]

    async def list_alerts(self, query: ListAlertsQuery) -> list[AlertView]:
        self.last_alerts_query = query
        return self._alerts[query.offset : query.offset + query.limit]

    async def daily_metrics(
        self, query: GetDailyMetricsQuery
    ) -> list[DailyMetric]:
        return list(self._daily)

    async def summary_metrics(
        self, query: GetSummaryMetricsQuery
    ) -> SummaryMetric:
        return self._summary
