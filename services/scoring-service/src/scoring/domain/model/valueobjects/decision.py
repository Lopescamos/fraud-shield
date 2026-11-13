from __future__ import annotations

from enum import Enum


class Decision(str, Enum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"

    @classmethod
    def from_score(cls, score: int) -> Decision:
        """Map a 0..100 risk score to a decision using ADR-007 thresholds."""
        if score < 0 or score > 100:
            raise ValueError("[Decision] score must be within 0..100")
        if score < 40:
            return cls.APPROVE
        if score < 90:
            return cls.REVIEW
        return cls.BLOCK


_LEVELS = (
    (40, "LOW"),
    (70, "MEDIUM"),
    (90, "HIGH"),
    (101, "CRITICAL"),
)


def level_from_score(score: int) -> str:
    """Bucket the score into the risk levels defined in ADR-007."""
    if score < 0 or score > 100:
        raise ValueError("[level_from_score] score must be within 0..100")
    for upper, name in _LEVELS:
        if score < upper:
            return name
    return "CRITICAL"
