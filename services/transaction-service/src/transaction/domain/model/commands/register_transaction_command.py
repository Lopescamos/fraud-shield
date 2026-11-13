from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from transaction.domain.model.valueobjects.channel import Channel


@dataclass(frozen=True, slots=True)
class RegisterTransactionCommand:
    account_id: str
    amount: Decimal
    currency: str
    channel: Channel
    occurred_at: datetime
    device_id: str | None = None
