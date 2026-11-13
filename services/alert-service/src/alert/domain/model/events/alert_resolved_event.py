from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AlertResolvedEvent:
    """Internal domain event. ``new_status`` is either RESOLVED or
    DISMISSED; ``reason`` is the resolution notes or the dismissal
    reason, both non-empty by invariant."""

    alert_id: UUID
    transaction_id: UUID
    previous_status: str
    new_status: str
    analyst_id: UUID
    reason: str
    closed_at: datetime
