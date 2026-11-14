from __future__ import annotations

from typing import Protocol

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


class AnalyticsReadRepository(Protocol):
    """Read side of the projection store. All methods are pure queries,
    never write."""

    async def list_transactions(
        self, query: ListTransactionsQuery
    ) -> list[TransactionView]: ...

    async def list_alerts(self, query: ListAlertsQuery) -> list[AlertView]: ...

    async def daily_metrics(
        self, query: GetDailyMetricsQuery
    ) -> list[DailyMetric]: ...

    async def summary_metrics(
        self, query: GetSummaryMetricsQuery
    ) -> SummaryMetric: ...
