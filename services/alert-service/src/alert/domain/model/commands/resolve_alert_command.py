from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResolveAlertCommand:
    alert_id: UUID
    resolution_notes: str
