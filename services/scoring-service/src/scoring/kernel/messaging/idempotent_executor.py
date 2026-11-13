from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import UUID


class ProcessedEventStore(Protocol):
    async def already_processed(self, message_id: UUID, group: str) -> bool: ...
    async def mark_processed(self, message_id: UUID, group: str) -> None: ...


class IdempotentExecutor:
    """
    Runs an operation at most once for a given (message_id, consumer_group).
    The store writes the marker in the SAME transaction as the operation.
    """

    def __init__(self, store: ProcessedEventStore) -> None:
        self._store = store

    async def run_once(
        self,
        message_id: UUID,
        group: str,
        operation: Callable[[], Awaitable[None]],
    ) -> None:
        if await self._store.already_processed(message_id, group):
            return
        await operation()
        await self._store.mark_processed(message_id, group)
