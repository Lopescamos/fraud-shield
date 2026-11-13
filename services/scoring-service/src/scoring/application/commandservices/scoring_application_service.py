from __future__ import annotations

from typing import Protocol
from uuid import UUID

from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.kernel.application.result import ApplicationError, Result


class ScoringApplicationService(Protocol):
    async def handle(
        self,
        command: ScoreTransactionCommand,
        idempotency_key: str | None = None,
    ) -> Result[UUID, ApplicationError]: ...
