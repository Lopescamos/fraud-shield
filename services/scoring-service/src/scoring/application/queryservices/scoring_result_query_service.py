from __future__ import annotations

from typing import Protocol

from scoring.domain.model.aggregates.scoring_result import ScoringResult
from scoring.domain.model.queries.get_scoring_result_by_id_query import (
    GetScoringResultByIdQuery,
)


class ScoringResultQueryService(Protocol):
    async def handle(
        self, query: GetScoringResultByIdQuery
    ) -> ScoringResult | None: ...
