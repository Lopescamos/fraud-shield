"""Transaction received event, published by transaction-service."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransactionReceivedV1(BaseModel):
    """
    Emitted when `transaction-service` registers and persists a new
    transaction. `account_id_hash` is irreversible (hash + salt).

    Partition key: `account_id_hash`.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    transaction_id: UUID
    account_id_hash: str = Field(min_length=64, max_length=64)
    amount: Decimal
    currency: str = Field(min_length=3, max_length=3)
    channel: str
    device_id: str | None = None
    occurred_at: datetime
