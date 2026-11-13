from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

from alert.domain.model.aggregates.alert import Alert
from alert.domain.model.commands.assign_alert_command import AssignAlertCommand
from alert.domain.model.commands.dismiss_alert_command import DismissAlertCommand
from alert.domain.model.commands.raise_alert_from_score_command import (
    RaiseAlertFromScoreCommand,
)
from alert.domain.model.commands.resolve_alert_command import ResolveAlertCommand
from alert.domain.model.errors import InvalidAlertTransition
from alert.domain.repositories.alert_repository import AlertRepository
from alert.kernel.application.result import (
    ApplicationError,
    Failure,
    Result,
    Success,
)
from alert.kernel.application.transactional import transactional

logger = logging.getLogger(__name__)


class AlertApplicationServiceImpl:
    def __init__(
        self,
        session_factory: Any,
        repository_builder: Callable[[Any], AlertRepository],
    ) -> None:
        self._session_factory = session_factory
        self._repository_builder = repository_builder
        self._session: Any = None

    @transactional
    async def raise_from_score(
        self, command: RaiseAlertFromScoreCommand
    ) -> Result[UUID | None, ApplicationError]:
        if command.decision == "APPROVE":
            logger.info(
                "alert-skipped-decision-approve",
                extra={"transaction_id": str(command.transaction_id)},
            )
            return Success(None)

        repository = self._repository_builder(self._session)

        existing = await repository.find_by_transaction_id(command.transaction_id)
        if existing is not None:
            return Success(existing.id)

        try:
            alert = Alert.register(command)
        except ValueError as exc:
            return Failure(ApplicationError.validation_error("alert", str(exc)))

        try:
            saved = await repository.save(alert)
        except Exception as exc:
            return Failure(ApplicationError.unexpected("raise-alert", str(exc)))

        return Success(saved.id)

    @transactional
    async def assign(
        self, command: AssignAlertCommand
    ) -> Result[UUID, ApplicationError]:
        return await self._mutate(
            alert_id=command.alert_id,
            mutate=lambda alert: alert.assign(command.analyst_id),
            operation="assign-alert",
        )

    @transactional
    async def resolve(
        self, command: ResolveAlertCommand
    ) -> Result[UUID, ApplicationError]:
        return await self._mutate(
            alert_id=command.alert_id,
            mutate=lambda alert: alert.resolve(command.resolution_notes),
            operation="resolve-alert",
        )

    @transactional
    async def dismiss(
        self, command: DismissAlertCommand
    ) -> Result[UUID, ApplicationError]:
        return await self._mutate(
            alert_id=command.alert_id,
            mutate=lambda alert: alert.dismiss(command.reason),
            operation="dismiss-alert",
        )

    async def _mutate(
        self,
        *,
        alert_id: UUID,
        mutate: Callable[[Alert], None],
        operation: str,
    ) -> Result[UUID, ApplicationError]:
        repository = self._repository_builder(self._session)

        alert = await repository.find_by_id(alert_id)
        if alert is None:
            return Failure(ApplicationError.not_found("Alert", str(alert_id)))

        try:
            mutate(alert)
        except InvalidAlertTransition as exc:
            return Failure(
                ApplicationError.business_rule_violation("Alert", str(exc))
            )
        except ValueError as exc:
            return Failure(ApplicationError.validation_error("alert", str(exc)))

        try:
            saved = await repository.save(alert)
        except Exception as exc:
            return Failure(ApplicationError.unexpected(operation, str(exc)))

        return Success(saved.id)
