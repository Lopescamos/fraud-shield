from __future__ import annotations

from typing import Protocol
from uuid import UUID

from alert.domain.model.aggregates.alert import Alert
from alert.domain.model.queries.list_alerts_query import ListAlertsQuery


class AlertRepository(Protocol):
    async def find_by_id(self, id: UUID) -> Alert | None: ...

    async def find_by_transaction_id(
        self, transaction_id: UUID
    ) -> Alert | None: ...

    async def save(self, alert: Alert) -> Alert: ...

    async def list_by(self, query: ListAlertsQuery) -> list[Alert]: ...
