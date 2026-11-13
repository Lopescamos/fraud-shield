from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from shared_contracts.constants import TRANSACTIONS_SCORED_V1
from shared_contracts.envelope import Envelope
from shared_contracts.transactions.v1 import TransactionScoredV1
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from alert.application.commandservices.alert_application_service import (
    AlertApplicationService,
)
from alert.domain.model.commands.raise_alert_from_score_command import (
    RaiseAlertFromScoreCommand,
)
from alert.infrastructure.persistence.repositories.processed_event_store_impl import (
    ProcessedEventStoreImpl,
)
from alert.kernel.messaging.idempotent_executor import IdempotentExecutor

logger = logging.getLogger(__name__)


class TransactionScoredConsumer:
    """
    Kafka consumer for ``transactions.scored.v1``. Validates each envelope
    against ``TransactionScoredV1``, builds a ``RaiseAlertFromScoreCommand``
    and runs it through the application service. Idempotency is backed by
    ``alerts.processed_events``; the ``decision == APPROVE`` short-circuit
    lives in the application service, so APPROVE events still advance the
    offset and mark the marker cleanly.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        session_factory: async_sessionmaker[AsyncSession],
        service: AlertApplicationService,
        topic: str = TRANSACTIONS_SCORED_V1,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._topic = topic
        self._session_factory = session_factory
        self._service = service
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
            "transaction-scored-consumer-started",
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
        logger.info("transaction-scored-consumer-stopped")

    async def _run(self) -> None:
        assert self._consumer is not None
        while not self._stop_event.is_set():
            try:
                msg = await self._consumer.getone()
            except Exception:
                logger.exception("consumer-poll-failed")
                continue
            try:
                await self.handle_payload(msg.value)
                await self._consumer.commit()
            except Exception:
                logger.exception("consumer-handle-failed")

    async def handle_payload(self, raw: bytes | str | dict) -> None:
        """Entry point exposed for tests: pretend a message just arrived."""
        if isinstance(raw, bytes | bytearray):
            envelope_dict = json.loads(raw.decode("utf-8"))
        elif isinstance(raw, str):
            envelope_dict = json.loads(raw)
        else:
            envelope_dict = dict(raw)

        envelope = Envelope[TransactionScoredV1].model_validate(envelope_dict)
        payload = envelope.payload
        decision = _decision_from_score(payload.score)

        command = RaiseAlertFromScoreCommand(
            transaction_id=payload.transaction_id,
            scoring_result_id=payload.assessment_id,
            account_id_hash=payload.account_id_hash,
            risk_score=payload.score,
            level=payload.level,
            decision=decision,
            model_version=payload.model_version,
            scored_at=payload.occurred_at,
        )

        async with self._session_factory() as session:
            async with session.begin():
                executor = IdempotentExecutor(ProcessedEventStoreImpl(session))

                async def _execute() -> None:
                    await self._service.raise_from_score(command)

                await executor.run_once(
                    message_id=envelope.message_id,
                    group=self._group_id,
                    operation=_execute,
                )


def _decision_from_score(score: int) -> str:
    """Mirror of ``scoring-service`` Decision thresholds (ADR-007):
    APPROVE < 40, REVIEW 40..89, BLOCK >= 90. Duplicated here on purpose
    so alert-service does not depend on scoring."""
    if score < 40:
        return "APPROVE"
    if score < 90:
        return "REVIEW"
    return "BLOCK"
