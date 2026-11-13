from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

from shared_contracts.constants import TRANSACTIONS_RECEIVED_V1
from shared_contracts.envelope import Envelope
from shared_contracts.transactions.v1 import TransactionReceivedV1
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from scoring.application.commandservices.scoring_application_service import (
    ScoringApplicationService,
)
from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.infrastructure.persistence.repositories.processed_event_store_impl import (
    ProcessedEventStoreImpl,
)
from scoring.kernel.messaging.idempotent_executor import IdempotentExecutor

logger = logging.getLogger(__name__)


class TransactionReceivedConsumer:
    """
    Kafka consumer for ``transactions.received.v1``. Translates each
    envelope into a ``ScoreTransactionCommand`` and runs it through the
    ``ScoringApplicationService``. Idempotency is backed by
    ``scoring.processed_events``; the consumer group is passed in.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        session_factory: async_sessionmaker[AsyncSession],
        service_factory: Callable[[], ScoringApplicationService],
        topic: str = TRANSACTIONS_RECEIVED_V1,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._topic = topic
        self._session_factory = session_factory
        self._service_factory = service_factory
        self._consumer: Any | None = None
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        from aiokafka import AIOKafkaConsumer

        self._consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            enable_auto_commit=False,
        )
        await self._consumer.start()
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())
        logger.info(
            "transaction-received-consumer-started",
            extra={"topic": self._topic, "group_id": self._group_id},
        )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
        if self._task is not None:
            await self._task
            self._task = None
        logger.info("transaction-received-consumer-stopped")

    async def _run(self) -> None:
        assert self._consumer is not None
        while not self._stop_event.is_set():
            try:
                msg = await self._consumer.getone()
            except Exception:
                logger.exception("consumer-poll-failed")
                continue
            try:
                await self._handle(msg.value)
                await self._consumer.commit()
            except Exception:
                logger.exception("consumer-handle-failed")

    async def handle_payload(self, raw: bytes | str | dict) -> None:
        """Entry point exposed for tests: pretend a message just arrived."""
        await self._handle(raw)

    async def _handle(self, raw: bytes | str | dict) -> None:
        if isinstance(raw, bytes | bytearray):
            envelope_dict = json.loads(raw.decode("utf-8"))
        elif isinstance(raw, str):
            envelope_dict = json.loads(raw)
        else:
            envelope_dict = dict(raw)

        envelope = Envelope[TransactionReceivedV1].model_validate(envelope_dict)

        async with self._session_factory() as session:
            async with session.begin():
                executor = IdempotentExecutor(ProcessedEventStoreImpl(session))

                async def _execute() -> None:
                    command = ScoreTransactionCommand(
                        transaction_id=envelope.payload.transaction_id,
                        account_id_hash=envelope.payload.account_id_hash,
                        amount=envelope.payload.amount,
                        currency=envelope.payload.currency,
                        channel=envelope.payload.channel,
                        occurred_at=envelope.payload.occurred_at,
                        device_id=envelope.payload.device_id,
                    )
                    service = self._service_factory()
                    await service.handle(command)

                await executor.run_once(
                    message_id=envelope.message_id,
                    group=self._group_id,
                    operation=_execute,
                )
