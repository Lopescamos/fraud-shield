from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetAlertByIdQuery:
    alert_id: UUID
