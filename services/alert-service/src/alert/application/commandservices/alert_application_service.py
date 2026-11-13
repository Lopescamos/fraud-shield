from __future__ import annotations

from typing import Protocol
from uuid import UUID

from alert.domain.model.commands.assign_alert_command import AssignAlertCommand
from alert.domain.model.commands.dismiss_alert_command import DismissAlertCommand
from alert.domain.model.commands.raise_alert_from_score_command import (
    RaiseAlertFromScoreCommand,
)
from alert.domain.model.commands.resolve_alert_command import ResolveAlertCommand
from alert.kernel.application.result import ApplicationError, Result


class AlertApplicationService(Protocol):
    async def raise_from_score(
        self, command: RaiseAlertFromScoreCommand
    ) -> Result[UUID | None, ApplicationError]:
        """Returns ``Success(alert_id)`` when the alert was created,
        ``Success(existing_id)`` if it already existed for that
        transaction, or ``Success(None)`` when the ``decision`` was
        APPROVE (no-op idempotente)."""

    async def assign(
        self, command: AssignAlertCommand
    ) -> Result[UUID, ApplicationError]: ...

    async def resolve(
        self, command: ResolveAlertCommand
    ) -> Result[UUID, ApplicationError]: ...

    async def dismiss(
        self, command: DismissAlertCommand
    ) -> Result[UUID, ApplicationError]: ...
