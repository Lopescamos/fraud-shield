from __future__ import annotations

from uuid import UUID

from transaction.domain.model.aggregates.transaction import Transaction


class FakeTransactionRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, Transaction] = {}
        self._idempotency: dict[str, UUID] = {}
        self.published_events: list = []

    async def find_by_id(self, id: UUID) -> Transaction | None:
        return self._store.get(id)

    async def save(self, transaction: Transaction) -> Transaction:
        self.published_events.extend(transaction.pull_events())
        self._store[transaction.id] = transaction
        return transaction

    async def find_by_idempotency_key(self, key: str) -> UUID | None:
        return self._idempotency.get(key)

    async def save_idempotency_key(self, key: str, transaction_id: UUID) -> None:
        self._idempotency[key] = transaction_id
