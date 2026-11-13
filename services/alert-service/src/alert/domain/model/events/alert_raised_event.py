from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AlertRaisedEvent:
    """Internal domain event. The application layer translates it to
    ``AlertRaisedV1``."""

    alert_id: UUID
    transaction_id: UUID
    account_id_hash: str
    severity: str
    score: int
    level: str
    opened_at: datetime
