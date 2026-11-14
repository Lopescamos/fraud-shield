from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.infrastructure.persistence.entities.processed_event_entity import (
    ProcessedEventEntity,
)
from analytics.kernel.messaging.idempotent_executor import ProcessedEventStore


class ProcessedEventStoreImpl(ProcessedEventStore):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def already_processed(self, message_id: UUID, group: str) -> bool:
        stmt = select(ProcessedEventEntity).where(
            ProcessedEventEntity.message_id == message_id,
            ProcessedEventEntity.consumer_group == group,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def mark_processed(self, message_id: UUID, group: str) -> None:
        self._session.add(
            ProcessedEventEntity(
                message_id=message_id,
                consumer_group=group,
            )
        )
        await self._session.flush()
