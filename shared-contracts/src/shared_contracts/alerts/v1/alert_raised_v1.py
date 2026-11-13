"""Alert raised event, published by alert-service."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertRaisedV1(BaseModel):
    """
    Emitted by `alert-service` when a `FraudAlert` is opened as a reaction
    to a high/critical `TransactionScoredV1`.

    Partition key: `alert_id`.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    alert_id: UUID
    transaction_id: UUID
    account_id_hash: str = Field(min_length=64, max_length=64)
    severity: str
    score: int = Field(ge=0, le=100)
    level: str
    opened_at: datetime
