from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from scoring.domain.services.model_registry import ActiveModel, ModelRegistry
from scoring.infrastructure.persistence.entities.model_registry_persistence_entity import (
    ModelRegistryPersistenceEntity,
)


class ModelRegistryAdapter(ModelRegistry):
    """Queries ``scoring.model_registry`` for the currently active model
    of a given algorithm."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_active(self, algorithm: str) -> ActiveModel | None:
        async with self._session_factory() as session:
            stmt = (
                select(ModelRegistryPersistenceEntity)
                .where(ModelRegistryPersistenceEntity.algorithm == algorithm)
                .where(ModelRegistryPersistenceEntity.is_active.is_(True))
            )
            entity = (await session.execute(stmt)).scalar_one_or_none()
            if entity is None:
                return None
            return ActiveModel(
                algorithm=entity.algorithm,
                version=entity.version,
                metrics=entity.metrics or {},
            )
