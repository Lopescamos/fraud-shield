from __future__ import annotations

from typing import Protocol

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


class QueryApplicationService(Protocol):
    async def list_transactions(
        self, query: ListTransactionsQuery
    ) -> list[TransactionDTO]: ...

    async def list_alerts(self, query: ListAlertsQuery) -> list[AlertDTO]: ...

    async def daily_metrics(
        self, query: GetDailyMetricsQuery
    ) -> list[DailyMetricDTO]: ...

    async def summary_metrics(
        self, query: GetSummaryMetricsQuery
    ) -> SummaryMetricDTO: ...
