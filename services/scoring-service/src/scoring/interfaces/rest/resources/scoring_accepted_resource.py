from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ScoringAcceptedResource(BaseModel):
    scoring_result_id: UUID
