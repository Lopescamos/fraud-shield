from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from alert.domain.model.aggregates.alert import Alert
from alert.domain.model.queries.list_alerts_query import ListAlertsQuery
from alert.domain.repositories.alert_repository import AlertRepository
from alert.infrastructure.persistence.assemblers.alert_persistence_assembler import (
    AlertPersistenceAssembler as Mapper,
)
from alert.infrastructure.persistence.entities.alert_persistence_entity import (
    AlertPersistenceEntity,
)
from alert.kernel.domain.event_dispatcher import EventDispatcher


class AlertRepositoryImpl(AlertRepository):
    def __init__(self, session: AsyncSession, dispatcher: EventDispatcher) -> None:
        self._session = session
        self._dispatcher = dispatcher

    async def find_by_id(self, id: UUID) -> Alert | None:
        stmt = select(AlertPersistenceEntity).where(
            AlertPersistenceEntity.id == id
        )
        entity = (await self._session.execute(stmt)).scalar_one_or_none()
        return Mapper.to_domain(entity) if entity else None

    async def find_by_transaction_id(
        self, transaction_id: UUID
    ) -> Alert | None:
        stmt = select(AlertPersistenceEntity).where(
            AlertPersistenceEntity.transaction_id == transaction_id
        )
        entity = (await self._session.execute(stmt)).scalar_one_or_none()
        return Mapper.to_domain(entity) if entity else None

    async def save(self, alert: Alert) -> Alert:
        events = alert.pull_events()
        entity = Mapper.to_persistence(alert)

        # Upsert so repeat calls on the same aggregate update instead of
        # inserting (and tripping the unique transaction_id index).
        values = {
            column.name: getattr(entity, column.name)
            for column in AlertPersistenceEntity.__table__.columns
            if column.name not in ("created_at", "updated_at")
            and getattr(entity, column.name) is not None
        }
        stmt = (
            insert(AlertPersistenceEntity)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[AlertPersistenceEntity.id],
                set_={
                    k: v
                    for k, v in values.items()
                    if k not in ("id", "transaction_id", "opened_at")
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

        for event in events:
            await self._dispatcher.dispatch(event)
        return alert

    async def list_by(self, query: ListAlertsQuery) -> list[Alert]:
        stmt = select(AlertPersistenceEntity)
        if query.status is not None:
            stmt = stmt.where(AlertPersistenceEntity.status == query.status.value)
        if query.priority is not None:
            stmt = stmt.where(AlertPersistenceEntity.priority == query.priority.value)
        stmt = (
            stmt.order_by(AlertPersistenceEntity.opened_at.desc())
            .offset(query.offset)
            .limit(query.limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [Mapper.to_domain(r) for r in rows]
