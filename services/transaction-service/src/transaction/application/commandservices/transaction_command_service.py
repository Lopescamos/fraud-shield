from __future__ import annotations

from typing import Protocol
from uuid import UUID

from transaction.domain.model.commands.register_transaction_command import (
    RegisterTransactionCommand,
)
from transaction.kernel.application.result import ApplicationError, Result


class TransactionCommandService(Protocol):
    async def handle(
        self,
        command: RegisterTransactionCommand,
        idempotency_key: str | None = None,
    ) -> Result[UUID, ApplicationError]: ...
