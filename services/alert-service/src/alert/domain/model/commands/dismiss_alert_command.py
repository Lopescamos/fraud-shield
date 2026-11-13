from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DismissAlertCommand:
    alert_id: UUID
    reason: str
