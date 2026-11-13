from __future__ import annotations

from enum import Enum


class AlertStatus(str, Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"

    def is_terminal(self) -> bool:
        return self in (AlertStatus.RESOLVED, AlertStatus.DISMISSED)
