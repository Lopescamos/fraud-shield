from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scoring.domain.model.aggregates.scoring_result import ScoringResult
from scoring.domain.repositories.scoring_result_repository import (
    ScoringResultRepository,
)
from scoring.infrastructure.persistence.assemblers.scoring_result_persistence_assembler import (
    ScoringResultPersistenceAssembler as Mapper,
)
from scoring.infrastructure.persistence.entities.scoring_result_persistence_entity import (
    ScoringResultPersistenceEntity,
)
from scoring.kernel.domain.event_dispatcher import EventDispatcher


class ScoringResultRepositoryImpl(ScoringResultRepository):
    def __init__(self, session: AsyncSession, dispatcher: EventDispatcher) -> None:
        self._session = session
        self._dispatcher = dispatcher

    async def find_by_id(self, id: UUID) -> ScoringResult | None:
        stmt = select(ScoringResultPersistenceEntity).where(
            ScoringResultPersistenceEntity.id == id
        )
        entity = (await self._session.execute(stmt)).scalar_one_or_none()
        return Mapper.to_domain(entity) if entity else None

    async def find_by_transaction_id(
        self, transaction_id: UUID
    ) -> ScoringResult | None:
        stmt = select(ScoringResultPersistenceEntity).where(
            ScoringResultPersistenceEntity.transaction_id == transaction_id
        )
        entity = (await self._session.execute(stmt)).scalar_one_or_none()
        return Mapper.to_domain(entity) if entity else None

    async def save(self, result: ScoringResult) -> ScoringResult:
        events = result.pull_events()
        entity = Mapper.to_persistence(result)
        self._session.add(entity)
        await self._session.flush()
        for event in events:
            await self._dispatcher.dispatch(event)
        return Mapper.to_domain(entity)
