from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class TransactionResource(BaseModel):
    transaction_id: UUID
    account_id_hash: str
    amount: Decimal
    currency: str
    channel: str
    occurred_at: datetime
    device_id: str | None = None
