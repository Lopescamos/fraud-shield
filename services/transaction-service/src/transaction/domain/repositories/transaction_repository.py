from __future__ import annotations

from typing import Protocol
from uuid import UUID

from transaction.domain.model.aggregates.transaction import Transaction


class TransactionRepository(Protocol):
    async def find_by_id(self, id: UUID) -> Transaction | None: ...

    async def save(self, transaction: Transaction) -> Transaction: ...

    async def find_by_idempotency_key(self, key: str) -> UUID | None: ...

    async def save_idempotency_key(self, key: str, transaction_id: UUID) -> None: ...
