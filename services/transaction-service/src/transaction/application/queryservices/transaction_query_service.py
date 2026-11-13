from __future__ import annotations

from typing import Protocol

from transaction.domain.model.aggregates.transaction import Transaction
from transaction.domain.model.queries.get_transaction_by_id_query import (
    GetTransactionByIdQuery,
)


class TransactionQueryService(Protocol):
    async def handle(self, query: GetTransactionByIdQuery) -> Transaction | None: ...
