from __future__ import annotations

from enum import Enum


class Priority(str, Enum):
    """
    Alert severity mapped from the incoming ``risk_score``. Thresholds
    (inclusive): ``>=90`` CRITICAL, ``>=75`` HIGH, ``>=50`` MEDIUM,
    rest LOW. Changing them is a business decision; keep the upstream
    bounds (0..100) in sync with ``TransactionScoredV1``.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_risk_score(cls, score: int) -> Priority:
        if score < 0 or score > 100:
            raise ValueError("[Priority] risk_score must be within 0..100")
        if score >= 90:
            return cls.CRITICAL
        if score >= 75:
            return cls.HIGH
        if score >= 50:
            return cls.MEDIUM
        return cls.LOW
