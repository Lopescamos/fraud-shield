from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScoreTransactionResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: UUID
    account_id_hash: str = Field(min_length=64, max_length=64)
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    channel: str = Field(min_length=1, max_length=16)
    occurred_at: datetime
    country: str | None = Field(default=None, max_length=3)
    device_id: str | None = Field(default=None, max_length=64)
    extra_features: dict[str, float] = Field(default_factory=dict)
