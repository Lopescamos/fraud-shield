from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from transaction.interfaces.rest.resources.register_transaction_resource import (
    RegisterTransactionResource,
)


class RegisterBatchTransactionsResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RegisterTransactionResource] = Field(min_length=1, max_length=500)


class BatchItemOutcomeResource(BaseModel):
    index: int
    transaction_id: UUID | None = None
    error: dict | None = None


class BatchAcceptedResource(BaseModel):
    outcomes: list[BatchItemOutcomeResource]
    accepted: int
    rejected: int
