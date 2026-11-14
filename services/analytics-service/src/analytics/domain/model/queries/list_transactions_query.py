from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from analytics.domain.model.valueobjects.decision import Decision


@dataclass(frozen=True, slots=True)
class ListTransactionsQuery:
    date_from: datetime | None = None
    date_to: datetime | None = None
    decision: Decision | None = None
    country: str | None = None
    limit: int = 100
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("[ListTransactionsQuery] limit must be within 1..1000")
        if self.offset < 0:
            raise ValueError("[ListTransactionsQuery] offset must be >= 0")
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("[ListTransactionsQuery] date_from must be <= date_to")
