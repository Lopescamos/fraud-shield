from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class GetDailyMetricsQuery:
    date_from: datetime
    date_to: datetime

    def __post_init__(self) -> None:
        if self.date_from > self.date_to:
            raise ValueError("[GetDailyMetricsQuery] date_from must be <= date_to")


@dataclass(frozen=True, slots=True)
class GetSummaryMetricsQuery:
    """No filters: returns cumulative totals across the whole dataset."""
