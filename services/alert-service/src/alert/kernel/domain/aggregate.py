from __future__ import annotations

from typing import Any


class AbstractDomainAggregateRoot:
    """
    Base class for aggregate roots. Tracks domain events in-memory.
    Subclasses are usually ``@dataclass``.
    """

    def _register_event(self, event: Any) -> None:
        events = getattr(self, "_events", None)
        if events is None:
            events = []
            object.__setattr__(self, "_events", events)
        events.append(event)

    def pull_events(self) -> list[Any]:
        events = list(getattr(self, "_events", []))
        if events:
            object.__setattr__(self, "_events", [])
        return events
