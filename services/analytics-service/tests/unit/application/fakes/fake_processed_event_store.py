from __future__ import annotations

from uuid import UUID


class FakeProcessedEventStore:
    def __init__(self) -> None:
        self.markers: set[tuple[UUID, str]] = set()

    async def already_processed(self, message_id: UUID, group: str) -> bool:
        return (message_id, group) in self.markers

    async def mark_processed(self, message_id: UUID, group: str) -> None:
        self.markers.add((message_id, group))
