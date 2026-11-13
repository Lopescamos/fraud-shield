from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from alert.infrastructure.persistence.entities.processed_event_persistence_entity import (
    ProcessedEventPersistenceEntity,
)
from alert.kernel.messaging.idempotent_executor import ProcessedEventStore


class ProcessedEventStoreImpl(ProcessedEventStore):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def already_processed(self, message_id: UUID, group: str) -> bool:
        stmt = select(ProcessedEventPersistenceEntity).where(
            ProcessedEventPersistenceEntity.message_id == message_id,
            ProcessedEventPersistenceEntity.consumer_group == group,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def mark_processed(self, message_id: UUID, group: str) -> None:
        self._session.add(
            ProcessedEventPersistenceEntity(
                message_id=message_id,
                consumer_group=group,
            )
        )
        await self._session.flush()
