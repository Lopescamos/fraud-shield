from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from analytics.domain.model.valueobjects.alert_status import AlertStatus
from analytics.domain.model.valueobjects.priority import Priority


@dataclass(frozen=True, slots=True)
class AlertView:
    """
    Read-model combining ``AlertRaisedV1`` and ``AlertResolvedV1`` on
    the same ``alert_id``. ``analyst_id``, ``resolution`` and
    ``closed_at`` are filled only after the alert is resolved or
    dismissed.
    """

    alert_id: UUID
    transaction_id: UUID
    account_id_hash: str
    priority: Priority
    score: int
    level: str
    status: AlertStatus
    opened_at: datetime
    analyst_id: UUID | None = None
    resolution: str | None = None
    closed_at: datetime | None = None
