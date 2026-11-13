from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ScoringResultRegisteredEvent:
    """
    Internal domain event. The application layer translates it to the
    integration contract ``TransactionScoredV1``.
    """

    scoring_result_id: UUID
    transaction_id: UUID
    account_id_hash: str
    score: int
    level: str
    decision: str
    rules_score: int
    xgb_probability: Decimal
    iforest_anomaly: Decimal
    degraded_mode: bool
    model_version: str
    occurred_at: datetime
