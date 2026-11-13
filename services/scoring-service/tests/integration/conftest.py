from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from scoring.infrastructure.messaging.outbox import outbox_persistence_entity  # noqa: F401
from scoring.infrastructure.persistence.entities import (  # noqa: F401
    model_registry_persistence_entity,
    processed_event_persistence_entity,
    scoring_result_persistence_entity,
)
from scoring.infrastructure.persistence.session import Base


def _docker_available() -> bool:
    try:
        import docker  # type: ignore
    except ImportError:
        return False
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def postgres_url() -> str:
    if not _docker_available():
        pytest.skip("Docker is not available; skipping integration tests.")
    from testcontainers.postgres import PostgresContainer

    container = PostgresContainer("postgres:16-alpine", driver="asyncpg")
    container.start()
    url = container.get_connection_url()
    os.environ["SCORING_DATABASE_URL"] = url
    yield url
    container.stop()


@pytest_asyncio.fixture(scope="session")
async def async_engine(postgres_url: str):
    engine = create_async_engine(postgres_url, future=True)
    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS scoring")
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(async_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def session(session_factory) -> AsyncIterator[AsyncSession]:
    async with session_factory() as s:
        yield s
