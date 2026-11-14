from __future__ import annotations

from datetime import UTC, datetime

import pytest

from analytics.domain.model.queries.daily_metrics_query import (
    GetDailyMetricsQuery,
)
from analytics.domain.model.queries.list_alerts_query import ListAlertsQuery
from analytics.domain.model.queries.list_transactions_query import (
    ListTransactionsQuery,
)


def test_list_transactions_rejects_bad_limit() -> None:
    with pytest.raises(ValueError, match="limit"):
        ListTransactionsQuery(limit=0)
    with pytest.raises(ValueError, match="limit"):
        ListTransactionsQuery(limit=1001)


def test_list_transactions_rejects_negative_offset() -> None:
    with pytest.raises(ValueError, match="offset"):
        ListTransactionsQuery(offset=-1)


def test_list_transactions_rejects_inverted_date_range() -> None:
    with pytest.raises(ValueError, match="date_from"):
        ListTransactionsQuery(
            date_from=datetime(2026, 11, 14, tzinfo=UTC),
            date_to=datetime(2026, 11, 13, tzinfo=UTC),
        )


def test_list_alerts_rejects_bad_limit() -> None:
    with pytest.raises(ValueError, match="limit"):
        ListAlertsQuery(limit=0)


def test_daily_metrics_rejects_inverted_range() -> None:
    with pytest.raises(ValueError, match="date_from"):
        GetDailyMetricsQuery(
            date_from=datetime(2026, 11, 14, tzinfo=UTC),
            date_to=datetime(2026, 11, 13, tzinfo=UTC),
        )
