from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from transaction.domain.model.valueobjects.channel import Channel


class RegisterTransactionResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    channel: Channel
    occurred_at: datetime
    device_id: str | None = Field(default=None, max_length=64)
