from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from transaction.domain.model.aggregates.transaction import Transaction
from transaction.domain.model.commands.register_transaction_command import (
    RegisterTransactionCommand,
)
from transaction.domain.repositories.transaction_repository import TransactionRepository
from transaction.kernel.application.result import (
    ApplicationError,
    Failure,
    Result,
    Success,
)
from transaction.kernel.application.transactional import transactional


class TransactionCommandServiceImpl:
    def __init__(
        self,
        session_factory: Any,
        repository_builder: Callable[[Any], TransactionRepository],
    ) -> None:
        self._session_factory = session_factory
        self._repository_builder = repository_builder
        self._session: Any = None

    @transactional
    async def handle(
        self,
        command: RegisterTransactionCommand,
        idempotency_key: str | None = None,
    ) -> Result[UUID, ApplicationError]:
        repository = self._repository_builder(self._session)

        if idempotency_key is not None:
            existing = await repository.find_by_idempotency_key(idempotency_key)
            if existing is not None:
                return Success(existing)

        try:
            transaction = Transaction.register(command)
        except ValueError as exc:
            return Failure(ApplicationError.validation_error("transaction", str(exc)))

        try:
            saved = await repository.save(transaction)
        except Exception as exc:
            return Failure(
                ApplicationError.unexpected("register-transaction", str(exc))
            )

        if idempotency_key is not None:
            try:
                await repository.save_idempotency_key(idempotency_key, saved.id)
            except Exception as exc:
                return Failure(
                    ApplicationError.unexpected("save-idempotency-key", str(exc))
                )

        return Success(saved.id)
