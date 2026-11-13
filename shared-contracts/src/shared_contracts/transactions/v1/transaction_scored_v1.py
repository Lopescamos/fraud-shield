"""Transaction scored event, published by scoring-service."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransactionScoredV1(BaseModel):
    """
    Emitted by `scoring-service` after a `RiskAssessment` is produced for
    a transaction. Carries the final score, the risk level and the per-model
    contributions needed by downstream consumers (alert-service, analytics).

    Partition key: `account_id_hash`.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    assessment_id: UUID
    transaction_id: UUID
    account_id_hash: str = Field(min_length=64, max_length=64)
    score: int = Field(ge=0, le=100)
    level: str
    rules_score: int = Field(ge=0, le=100)
    xgb_probability: Decimal
    iforest_anomaly: Decimal
    degraded_mode: bool
    model_version: str
    occurred_at: datetime
