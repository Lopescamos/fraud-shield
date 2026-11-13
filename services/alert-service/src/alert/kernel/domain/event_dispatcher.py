from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

EventHandler = Callable[[Any], Awaitable[None]]


class EventDispatcher:
    """In-memory async event dispatcher. Handlers register per event type."""

    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = {}

    def register(self, event_type: type, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def dispatch(self, event: Any) -> None:
        for handler in self._handlers.get(type(event), []):
            await handler(event)
