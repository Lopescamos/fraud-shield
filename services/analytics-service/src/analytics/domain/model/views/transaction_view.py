from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from analytics.domain.model.valueobjects.decision import Decision


@dataclass(frozen=True, slots=True)
class TransactionView:
    """
    Read-model combining ``TransactionReceivedV1`` and
    ``TransactionScoredV1`` on the same ``transaction_id``. Fields
    sourced from the scored event are optional: a transaction that was
    received but not yet scored is still a valid row.
    """

    transaction_id: UUID
    account_id_hash: str
    amount: Decimal
    currency: str
    channel: str
    country: str | None
    device_id: str | None
    occurred_at: datetime
    received_at: datetime
    risk_score: int | None = None
    level: str | None = None
    decision: Decision | None = None
    model_version: str | None = None
    degraded_mode: bool | None = None
    scored_at: datetime | None = None
