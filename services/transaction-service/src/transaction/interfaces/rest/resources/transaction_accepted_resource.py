from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class TransactionAcceptedResource(BaseModel):
    transaction_id: UUID
