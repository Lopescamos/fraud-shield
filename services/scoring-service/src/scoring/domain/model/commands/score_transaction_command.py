from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ScoreTransactionCommand:
    """
    Input to score a single transaction. Features are the ones the rules
    engine and ML adapters know how to consume; new features go here and
    into the vectorizer at the same time.
    """

    transaction_id: UUID
    account_id_hash: str
    amount: Decimal
    currency: str
    channel: str
    occurred_at: datetime
    country: str | None = None
    device_id: str | None = None
    extra_features: dict[str, float] = field(default_factory=dict)
