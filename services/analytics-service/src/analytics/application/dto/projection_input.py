from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TransactionReceivedInput:
    message_id: UUID
    transaction_id: UUID
    account_id_hash: str
    amount: Decimal
    currency: str
    channel: str
    country: str | None
    device_id: str | None
    occurred_at: datetime
    received_at: datetime


@dataclass(frozen=True, slots=True)
class TransactionScoredInput:
    message_id: UUID
    transaction_id: UUID
    account_id_hash: str
    risk_score: int
    level: str
    decision: str
    model_version: str
    degraded_mode: bool
    scored_at: datetime


@dataclass(frozen=True, slots=True)
class AlertRaisedInput:
    message_id: UUID
    alert_id: UUID
    transaction_id: UUID
    account_id_hash: str
    severity: str
    score: int
    level: str
    opened_at: datetime


@dataclass(frozen=True, slots=True)
class AlertResolvedInput:
    message_id: UUID
    alert_id: UUID
    transaction_id: UUID
    previous_status: str
    new_status: str
    analyst_id: UUID
    reason: str | None
    closed_at: datetime
