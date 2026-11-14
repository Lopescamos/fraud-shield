from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class TransactionResource(BaseModel):
    transaction_id: UUID
    account_id_hash: str
    amount: Decimal
    currency: str
    channel: str
    country: str | None
    device_id: str | None
    occurred_at: datetime
    received_at: datetime
    risk_score: int | None
    level: str | None
    decision: str | None
    model_version: str | None
    degraded_mode: bool | None
    scored_at: datetime | None


class AlertResource(BaseModel):
    alert_id: UUID
    transaction_id: UUID
    account_id_hash: str
    priority: str
    score: int
    level: str
    status: str
    opened_at: datetime
    analyst_id: UUID | None
    resolution: str | None
    closed_at: datetime | None


class DailyMetricResource(BaseModel):
    day: date
    transactions: int
    alerts: int
    blocked: int
    fraud_rate: float
    priority_low: int
    priority_medium: int
    priority_high: int
    priority_critical: int


class SummaryMetricResource(BaseModel):
    total_transactions: int
    total_alerts: int
    open_alerts: int
    in_review_alerts: int
    resolved_alerts: int
    dismissed_alerts: int
    blocked_transactions: int
    review_transactions: int
    fraud_rate: float
