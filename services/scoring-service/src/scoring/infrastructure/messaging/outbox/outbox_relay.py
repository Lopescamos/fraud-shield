from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from scoring.infrastructure.messaging.outbox.kafka_broker_publisher import (
    KafkaBrokerPublisher,
)
from scoring.infrastructure.messaging.outbox.outbox_persistence_entity import (
    OutboxPersistenceEntity,
)

logger = logging.getLogger(__name__)


class OutboxRelay:
    """
    Polls ``scoring.outbox_events`` for PENDING rows and publishes them
    to Kafka. Marks each row PUBLISHED on success, FAILED after reaching
    the max retry count. Stays dormant until SCORING_OUTBOX_RELAY_ENABLED
    is true and Kafka is reachable.
    """

    _MAX_ATTEMPTS = 5

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        broker: KafkaBrokerPublisher,
        interval_ms: int = 500,
        batch_size: int = 50,
    ) -> None:
        self._session_factory = session_factory
        self._broker = broker
        self._interval = interval_ms / 1000.0
        self._batch_size = batch_size
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        await self._broker.start()
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())
        logger.info("outbox-relay-started")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task
            self._task = None
        await self._broker.stop()
        logger.info("outbox-relay-stopped")

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._drain_once()
            except Exception:
                logger.exception("outbox-relay-iteration-failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval)
            except asyncio.TimeoutError:
                continue

    async def _drain_once(self) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                rows = (
                    await session.execute(
                        select(OutboxPersistenceEntity)
                        .where(OutboxPersistenceEntity.status == "PENDING")
                        .order_by(OutboxPersistenceEntity.created_at)
                        .limit(self._batch_size)
                        .with_for_update(skip_locked=True)
                    )
                ).scalars().all()

                for row in rows:
                    try:
                        await self._broker.publish(
                            channel=row.channel,
                            key=row.message_key,
                            envelope=row.payload,
                        )
                        row.status = "PUBLISHED"
                        row.published_at = datetime.now(UTC)
                    except Exception:
                        logger.exception("outbox-relay-publish-failed")
                        row.attempts += 1
                        if row.attempts >= self._MAX_ATTEMPTS:
                            row.status = "FAILED"
