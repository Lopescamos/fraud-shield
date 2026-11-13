from __future__ import annotations

from uuid import UUID

from alert.domain.model.aggregates.alert import Alert
from alert.domain.model.queries.list_alerts_query import ListAlertsQuery


class FakeAlertRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Alert] = {}
        self._by_tx: dict[UUID, UUID] = {}
        self.published_events: list = []

    async def find_by_id(self, id: UUID) -> Alert | None:
        return self._by_id.get(id)

    async def find_by_transaction_id(
        self, transaction_id: UUID
    ) -> Alert | None:
        alert_id = self._by_tx.get(transaction_id)
        return self._by_id.get(alert_id) if alert_id else None

    async def save(self, alert: Alert) -> Alert:
        self.published_events.extend(alert.pull_events())
        self._by_id[alert.id] = alert
        self._by_tx[alert.transaction_id] = alert.id
        return alert

    async def list_by(self, query: ListAlertsQuery) -> list[Alert]:
        items = list(self._by_id.values())
        if query.status is not None:
            items = [a for a in items if a.status is query.status]
        if query.priority is not None:
            items = [a for a in items if a.priority is query.priority]
        return items[query.offset : query.offset + query.limit]
