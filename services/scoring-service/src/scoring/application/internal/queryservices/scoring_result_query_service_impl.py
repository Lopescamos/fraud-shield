from __future__ import annotations

from collections.abc import Callable
from typing import Any

from scoring.domain.model.aggregates.scoring_result import ScoringResult
from scoring.domain.model.queries.get_scoring_result_by_id_query import (
    GetScoringResultByIdQuery,
)
from scoring.domain.repositories.scoring_result_repository import (
    ScoringResultRepository,
)


class ScoringResultQueryServiceImpl:
    def __init__(
        self,
        session_factory: Any,
        repository_builder: Callable[[Any], ScoringResultRepository],
    ) -> None:
        self._session_factory = session_factory
        self._repository_builder = repository_builder

    async def handle(
        self, query: GetScoringResultByIdQuery
    ) -> ScoringResult | None:
        async with self._session_factory() as session:
            repository = self._repository_builder(session)
            return await repository.find_by_id(query.scoring_result_id)
