from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssignAlertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analyst_id: UUID


class ResolveAlertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution_notes: str = Field(min_length=1, max_length=1000)


class DismissAlertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=1000)


class AlertMutationResponse(BaseModel):
    alert_id: UUID
