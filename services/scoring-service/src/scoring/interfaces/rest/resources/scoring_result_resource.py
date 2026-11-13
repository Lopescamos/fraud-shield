from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class RiskFactorResource(BaseModel):
    feature: str
    weight: float
    direction: str
    source: str


class ScoringResultResource(BaseModel):
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
    factors: list[RiskFactorResource]
    occurred_at: datetime | None
