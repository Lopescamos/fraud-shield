from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from transaction.domain.model.aggregates.transaction import Transaction
from transaction.domain.repositories.transaction_repository import TransactionRepository
from transaction.infrastructure.persistence.assemblers.transaction_persistence_assembler import (
    TransactionPersistenceAssembler as Mapper,
)
from transaction.infrastructure.persistence.entities.idempotency_key_persistence_entity import (
    IdempotencyKeyPersistenceEntity,
)
from transaction.infrastructure.persistence.entities.transaction_persistence_entity import (
    TransactionPersistenceEntity,
)
from transaction.kernel.domain.event_dispatcher import EventDispatcher


class TransactionRepositoryImpl(TransactionRepository):
    def __init__(self, session: AsyncSession, dispatcher: EventDispatcher) -> None:
        self._session = session
        self._dispatcher = dispatcher

    async def find_by_id(self, id: UUID) -> Transaction | None:
        stmt = select(TransactionPersistenceEntity).where(
            TransactionPersistenceEntity.id == id
        )
        entity = (await self._session.execute(stmt)).scalar_one_or_none()
        return Mapper.to_domain(entity) if entity else None

    async def save(self, transaction: Transaction) -> Transaction:
        events = transaction.pull_events()
        entity = Mapper.to_persistence(transaction)
        self._session.add(entity)
        await self._session.flush()
        for event in events:
            await self._dispatcher.dispatch(event)
        return Mapper.to_domain(entity)

    async def find_by_idempotency_key(self, key: str) -> UUID | None:
        stmt = select(IdempotencyKeyPersistenceEntity.transaction_id).where(
            IdempotencyKeyPersistenceEntity.key == key
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def save_idempotency_key(self, key: str, transaction_id: UUID) -> None:
        self._session.add(
            IdempotencyKeyPersistenceEntity(key=key, transaction_id=transaction_id)
        )
        await self._session.flush()
