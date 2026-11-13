from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from alert.application.internal.outboundservices.messaging.message_publisher import (
    MessagePublisher,
)
from alert.infrastructure.messaging.outbox.outbox_persistence_entity import (
    OutboxPersistenceEntity,
)


def _default_trace_id() -> str:
    return "00000000-0000-0000-0000-000000000000"


class OutboxMessagePublisher(MessagePublisher):
    """Writes the integration message into ``alerts.outbox_events`` using
    the current session. The relay job (disabled until Kafka is up) is
    the only piece that actually talks to the broker."""

    def __init__(
        self,
        session: AsyncSession,
        trace_id_provider: Callable[[], str] | None = None,
    ) -> None:
        self._session = session
        self._trace_id = trace_id_provider or _default_trace_id

    async def publish(
        self,
        channel: str,
        key: str,
        message_type: str,
        schema_version: int,
        payload: Any,
    ) -> None:
        message_id = uuid4()
        payload_dict = (
            payload.model_dump(mode="json")
            if hasattr(payload, "model_dump")
            else payload
        )
        envelope = {
            "message_id": str(message_id),
            "message_type": message_type,
            "schema_version": schema_version,
            "occurred_at": datetime.now(UTC).isoformat(),
            "trace_id": self._trace_id(),
            "payload": payload_dict,
        }
        self._session.add(
            OutboxPersistenceEntity(
                message_id=message_id,
                channel=channel,
                message_key=key,
                message_type=message_type,
                schema_version=schema_version,
                payload=envelope,
            )
        )
