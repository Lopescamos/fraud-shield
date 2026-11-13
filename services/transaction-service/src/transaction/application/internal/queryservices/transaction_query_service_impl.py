from __future__ import annotations

from collections.abc import Callable
from typing import Any

from transaction.domain.model.aggregates.transaction import Transaction
from transaction.domain.model.queries.get_transaction_by_id_query import (
    GetTransactionByIdQuery,
)
from transaction.domain.repositories.transaction_repository import TransactionRepository


class TransactionQueryServiceImpl:
    def __init__(
        self,
        session_factory: Any,
        repository_builder: Callable[[Any], TransactionRepository],
    ) -> None:
        self._session_factory = session_factory
        self._repository_builder = repository_builder

    async def handle(self, query: GetTransactionByIdQuery) -> Transaction | None:
        async with self._session_factory() as session:
            repository = self._repository_builder(session)
            return await repository.find_by_id(query.transaction_id)
