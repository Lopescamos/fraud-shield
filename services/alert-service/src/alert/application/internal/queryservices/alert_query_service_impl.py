from __future__ import annotations

from collections.abc import Callable
from typing import Any

from alert.domain.model.aggregates.alert import Alert
from alert.domain.model.queries.get_alert_by_id_query import GetAlertByIdQuery
from alert.domain.model.queries.list_alerts_query import ListAlertsQuery
from alert.domain.repositories.alert_repository import AlertRepository


class AlertQueryServiceImpl:
    def __init__(
        self,
        session_factory: Any,
        repository_builder: Callable[[Any], AlertRepository],
    ) -> None:
        self._session_factory = session_factory
        self._repository_builder = repository_builder

    async def get_by_id(self, query: GetAlertByIdQuery) -> Alert | None:
        async with self._session_factory() as session:
            repository = self._repository_builder(session)
            return await repository.find_by_id(query.alert_id)

    async def list(self, query: ListAlertsQuery) -> list[Alert]:
        async with self._session_factory() as session:
            repository = self._repository_builder(session)
            return await repository.list_by(query)
