from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TransactionRegisteredEvent:
    transaction_id: UUID
    account_id_hash: str
    amount: Decimal
    currency: str
    channel: str
    device_id: str | None
    occurred_at: datetime
