from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from alert.domain.model.valueobjects.risk_factor import RiskFactor


@dataclass(frozen=True, slots=True)
class RaiseAlertFromScoreCommand:
    """Input built by the TransactionScored consumer (or by a manual
    REST endpoint if we ever wire one). Carries everything the alert
    needs to be opened, including the factors so the analyst sees the
    'why' from day one."""

    transaction_id: UUID
    scoring_result_id: UUID
    account_id_hash: str
    risk_score: int
    level: str
    decision: str
    model_version: str
    scored_at: datetime
    factors: list[RiskFactor] = field(default_factory=list)
