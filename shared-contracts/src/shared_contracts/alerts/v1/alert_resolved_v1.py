"""Alert resolved event, published by alert-service."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AlertResolvedV1(BaseModel):
    """
    Emitted by `alert-service` when a `FraudAlert` leaves the open flow:
    moves to `CONFIRMED` or `DISMISSED`.

    Partition key: `alert_id`.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    alert_id: UUID
    transaction_id: UUID
    previous_status: str
    new_status: str
    analyst_id: UUID
    reason: str | None = None
    closed_at: datetime
