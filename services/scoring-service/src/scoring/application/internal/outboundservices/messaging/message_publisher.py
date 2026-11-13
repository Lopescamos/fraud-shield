from __future__ import annotations

from typing import Any, Protocol


class MessagePublisher(Protocol):
    """
    Publishes an integration message to the rest of the system. The
    implementation must guarantee atomicity with the current transaction
    (Outbox pattern) and hide the broker technology.
    """

    async def publish(
        self,
        channel: str,
        key: str,
        message_type: str,
        schema_version: int,
        payload: Any,
    ) -> None: ...
