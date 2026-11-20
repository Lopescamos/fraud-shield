from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from transaction.domain.model.commands.register_batch_transactions_command import (
    RegisterBatchTransactionsCommand,
)
from transaction.kernel.application.result import ApplicationError


@dataclass(frozen=True, slots=True)
class BatchItemOutcome:
    """Per-item outcome of a batch submission: either a persisted
    ``transaction_id`` or the ``ApplicationError`` that caused the
    item to be skipped. Order matches the order of the input."""

    index: int
    transaction_id: UUID | None
    error: ApplicationError | None

    @property
    def ok(self) -> bool:
        return self.transaction_id is not None


class TransactionBatchCommandService(Protocol):
    async def handle(
        self,
        command: RegisterBatchTransactionsCommand,
        idempotency_key: str | None = None,
    ) -> list[BatchItemOutcome]: ...
