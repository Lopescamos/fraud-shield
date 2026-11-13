from __future__ import annotations

from typing import Protocol

from alert.domain.model.aggregates.alert import Alert
from alert.domain.model.queries.get_alert_by_id_query import GetAlertByIdQuery
from alert.domain.model.queries.list_alerts_query import ListAlertsQuery


class AlertQueryService(Protocol):
    async def get_by_id(self, query: GetAlertByIdQuery) -> Alert | None: ...

    async def list(self, query: ListAlertsQuery) -> list[Alert]: ...
