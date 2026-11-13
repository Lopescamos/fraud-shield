from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RiskFactorResource(BaseModel):
    feature: str
    weight: float
    direction: str
    source: str


class AlertResource(BaseModel):
    alert_id: UUID
    transaction_id: UUID
    scoring_result_id: UUID
    account_id_hash: str
    risk_score: int
    level: str
    decision: str
    model_version: str
    priority: str
    status: str
    factors: list[RiskFactorResource]
    analyst_id: UUID | None
    resolution: str | None
    opened_at: datetime | None
    closed_at: datetime | None
