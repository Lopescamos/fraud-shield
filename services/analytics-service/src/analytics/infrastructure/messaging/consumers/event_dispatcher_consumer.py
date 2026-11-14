from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from shared_contracts.alerts.v1 import AlertRaisedV1, AlertResolvedV1
from shared_contracts.constants import (
    ALERTS_RAISED_V1,
    ALERTS_RESOLVED_V1,
    TRANSACTIONS_RECEIVED_V1,
    TRANSACTIONS_SCORED_V1,
)
from shared_contracts.envelope import Envelope
from shared_contracts.transactions.v1 import TransactionReceivedV1, TransactionScoredV1

from analytics.application.commandservices.projection_application_service import (
    ProjectionApplicationService,
)
from analytics.application.dto.projection_input import (
    AlertRaisedInput,
    AlertResolvedInput,
    TransactionReceivedInput,
    TransactionScoredInput,
)

logger = logging.getLogger(__name__)


# Consumer-group names match ADR-002 / shared_contracts.constants.
GROUP_RECEIVED = "analytics.ingest-received"
GROUP_SCORED = "analytics.ingest-scored"
GROUP_ALERTS = "analytics.ingest-alerts"


class EventDispatcherConsumer:
    """
    Subscribes to the four analytics topics on one consumer and
    dispatches each envelope to the right projector by topic. One
    consumer per service keeps rebalancing simple; per-topic offsets are
    still isolated because we commit after each message.

    All four subscriptions share the same ``bootstrap_servers``; the
    ``group_id`` is namespaced with a suffix so each topic keeps its own
    marker in ``analytics.processed_events``.
    """

    _TOPIC_TO_GROUP: dict[str, str] = {
        TRANSACTIONS_RECEIVED_V1: GROUP_RECEIVED,
        TRANSACTIONS_SCORED_V1: GROUP_SCORED,
        ALERTS_RAISED_V1: GROUP_ALERTS,
        ALERTS_RESOLVED_V1: GROUP_ALERTS,
    }

    def __init__(
        self,
        bootstrap_servers: str,
        service: ProjectionApplicationService,
        group_id_prefix: str = "analytics.ingest",
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._service = service
        self._group_id_prefix = group_id_prefix
        self._consumer: Any | None = None
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        from aiokafka import AIOKafkaConsumer

        self._consumer = AIOKafkaConsumer(
            *self._TOPIC_TO_GROUP.keys(),
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id_prefix,
            enable_auto_commit=False,
        )
        await self._consumer.start()
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())
        logger.info(
            "analytics-consumer-started",
            extra={
                "topics": list(self._TOPIC_TO_GROUP.keys()),
                "group_id_prefix": self._group_id_prefix,
            },
        )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
        if self._task is not None:
            await self._task
            self._task = None
        logger.info("analytics-consumer-stopped")

    async def _run(self) -> None:
        assert self._consumer is not None
        while not self._stop_event.is_set():
            try:
                msg = await self._consumer.getone()
            except Exception:
                logger.exception("consumer-poll-failed")
                continue
            try:
                await self.dispatch(msg.topic, msg.value)
                await self._consumer.commit()
            except Exception:
                logger.exception(
                    "consumer-handle-failed", extra={"topic": msg.topic}
                )

    async def dispatch(self, topic: str, raw: bytes | str | dict) -> None:
        """Entry point used by tests: pretend a message on ``topic``
        just arrived, no Kafka required."""
        if topic == TRANSACTIONS_RECEIVED_V1:
            env = _decode(raw, TransactionReceivedV1)
            await self._service.on_transaction_received(
                _build_received_input(env), GROUP_RECEIVED
            )
            return
        if topic == TRANSACTIONS_SCORED_V1:
            env = _decode(raw, TransactionScoredV1)
            await self._service.on_transaction_scored(
                _build_scored_input(env), GROUP_SCORED
            )
            return
        if topic == ALERTS_RAISED_V1:
            env = _decode(raw, AlertRaisedV1)
            await self._service.on_alert_raised(
                _build_alert_raised_input(env), GROUP_ALERTS
            )
            return
        if topic == ALERTS_RESOLVED_V1:
            env = _decode(raw, AlertResolvedV1)
            await self._service.on_alert_resolved(
                _build_alert_resolved_input(env), GROUP_ALERTS
            )
            return
        logger.warning("analytics-consumer-unknown-topic", extra={"topic": topic})


def _decode(raw: bytes | str | dict, payload_cls):
    if isinstance(raw, bytes | bytearray):
        envelope_dict = json.loads(raw.decode("utf-8"))
    elif isinstance(raw, str):
        envelope_dict = json.loads(raw)
    else:
        envelope_dict = dict(raw)
    return Envelope[payload_cls].model_validate(envelope_dict)


def _build_received_input(envelope) -> TransactionReceivedInput:
    payload = envelope.payload
    return TransactionReceivedInput(
        message_id=envelope.message_id,
        transaction_id=payload.transaction_id,
        account_id_hash=payload.account_id_hash,
        amount=payload.amount,
        currency=payload.currency,
        channel=payload.channel,
        country=getattr(payload, "country", None),
        device_id=payload.device_id,
        occurred_at=payload.occurred_at,
        received_at=envelope.occurred_at,
    )


def _build_scored_input(envelope) -> TransactionScoredInput:
    payload = envelope.payload
    return TransactionScoredInput(
        message_id=envelope.message_id,
        transaction_id=payload.transaction_id,
        account_id_hash=payload.account_id_hash,
        risk_score=payload.score,
        level=payload.level,
        decision=_decision_from_score(payload.score),
        model_version=payload.model_version,
        degraded_mode=payload.degraded_mode,
        scored_at=payload.occurred_at,
    )


def _build_alert_raised_input(envelope) -> AlertRaisedInput:
    payload = envelope.payload
    return AlertRaisedInput(
        message_id=envelope.message_id,
        alert_id=payload.alert_id,
        transaction_id=payload.transaction_id,
        account_id_hash=payload.account_id_hash,
        severity=payload.severity,
        score=payload.score,
        level=payload.level,
        opened_at=payload.opened_at,
    )


def _build_alert_resolved_input(envelope) -> AlertResolvedInput:
    payload = envelope.payload
    return AlertResolvedInput(
        message_id=envelope.message_id,
        alert_id=payload.alert_id,
        transaction_id=payload.transaction_id,
        previous_status=payload.previous_status,
        new_status=payload.new_status,
        analyst_id=payload.analyst_id,
        reason=payload.reason,
        closed_at=payload.closed_at,
    )


def _decision_from_score(score: int) -> str:
    """Mirror of ``scoring-service`` Decision thresholds (ADR-007):
    APPROVE < 40, REVIEW 40..89, BLOCK >= 90. Duplicated here on purpose
    so analytics-service does not depend on scoring."""
    if score < 40:
        return "APPROVE"
    if score < 90:
        return "REVIEW"
    return "BLOCK"
