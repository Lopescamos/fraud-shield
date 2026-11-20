from __future__ import annotations

from dataclasses import dataclass

from transaction.domain.model.commands.register_transaction_command import (
    RegisterTransactionCommand,
)


@dataclass(frozen=True, slots=True)
class RegisterBatchTransactionsCommand:
    """A batch of up to ``MAX_SIZE`` RegisterTransactionCommand. Any
    larger batch is rejected by the application layer (US-02)."""

    MAX_SIZE = 500

    items: list[RegisterTransactionCommand]
