from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AssignAlertCommand:
    alert_id: UUID
    analyst_id: UUID
