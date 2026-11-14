from __future__ import annotations

from dataclasses import dataclass

from analytics.domain.model.valueobjects.alert_status import AlertStatus
from analytics.domain.model.valueobjects.priority import Priority


@dataclass(frozen=True, slots=True)
class ListAlertsQuery:
    status: AlertStatus | None = None
    priority: Priority | None = None
    limit: int = 100
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("[ListAlertsQuery] limit must be within 1..1000")
        if self.offset < 0:
            raise ValueError("[ListAlertsQuery] offset must be >= 0")
