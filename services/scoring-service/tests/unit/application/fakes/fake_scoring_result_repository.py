from __future__ import annotations

from uuid import UUID

from scoring.domain.model.aggregates.scoring_result import ScoringResult


class FakeScoringResultRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, ScoringResult] = {}
        self._by_tx: dict[UUID, UUID] = {}
        self.published_events: list = []

    async def find_by_id(self, id: UUID) -> ScoringResult | None:
        return self._by_id.get(id)

    async def find_by_transaction_id(
        self, transaction_id: UUID
    ) -> ScoringResult | None:
        result_id = self._by_tx.get(transaction_id)
        return self._by_id.get(result_id) if result_id else None

    async def save(self, result: ScoringResult) -> ScoringResult:
        self.published_events.extend(result.pull_events())
        self._by_id[result.id] = result
        self._by_tx[result.transaction_id] = result.id
        return result
