"""Common message envelope wrapping every published event."""
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

P = TypeVar("P", bound=BaseModel)


class Envelope(BaseModel, Generic[P]):
    model_config = ConfigDict(extra="ignore")

    message_id: UUID
    message_type: str
    schema_version: int
    occurred_at: datetime
    trace_id: str
    payload: P
