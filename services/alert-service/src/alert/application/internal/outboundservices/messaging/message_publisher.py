from __future__ import annotations

from typing import Any, Protocol


class MessagePublisher(Protocol):
    """Publishes an integration message atomically with the current
    transaction (Outbox pattern)."""

    async def publish(
        self,
        channel: str,
        key: str,
        message_type: str,
        schema_version: int,
        payload: Any,
    ) -> None: ...
