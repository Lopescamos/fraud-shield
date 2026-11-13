from __future__ import annotations

from typing import Protocol
from uuid import UUID

from scoring.domain.model.aggregates.scoring_result import ScoringResult


class ScoringResultRepository(Protocol):
    async def find_by_id(self, id: UUID) -> ScoringResult | None: ...

    async def find_by_transaction_id(
        self, transaction_id: UUID
    ) -> ScoringResult | None: ...

    async def save(self, result: ScoringResult) -> ScoringResult: ...
