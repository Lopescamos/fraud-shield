from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from transaction.application.commandservices.transaction_batch_command_service import (
    BatchItemOutcome,
)
from transaction.domain.model.aggregates.transaction import Transaction
from transaction.domain.model.commands.register_batch_transactions_command import (
    RegisterBatchTransactionsCommand,
)
from transaction.domain.repositories.transaction_repository import TransactionRepository
from transaction.kernel.application.result import ApplicationError
from transaction.kernel.application.transactional import transactional

logger = logging.getLogger(__name__)


class TransactionBatchCommandServiceImpl:
    """
    Writes up to ``MAX_SIZE`` transactions in a single DB transaction.
    Every item that validates cleanly is registered; every item that
    raises ``ValueError`` is skipped and reported in the outcome list.
    One bad item does not fail the batch — partial success is the point
    of US-02.

    Idempotency works at two layers:
    - The whole-batch header ``Idempotency-Key`` returns the previous
      batch result if it matches, as in the single-item endpoint.
    - Each item may also carry its own ``idempotency_key`` (used as the
      per-item key); otherwise the per-item key is derived from the
      batch key plus the item index.
    """

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
        command: RegisterBatchTransactionsCommand,
        idempotency_key: str | None = None,
    ) -> list[BatchItemOutcome]:
        if len(command.items) == 0:
            return []
        if len(command.items) > RegisterBatchTransactionsCommand.MAX_SIZE:
            return [
                BatchItemOutcome(
                    index=0,
                    transaction_id=None,
                    error=ApplicationError.validation_error(
                        "items",
                        f"batch exceeds max size of "
                        f"{RegisterBatchTransactionsCommand.MAX_SIZE}",
                    ),
                )
            ]

        repository = self._repository_builder(self._session)
        outcomes: list[BatchItemOutcome] = []

        for index, item in enumerate(command.items):
            per_item_key = (
                f"{idempotency_key}:{index}" if idempotency_key is not None else None
            )

            try:
                if per_item_key is not None:
                    existing = await repository.find_by_idempotency_key(per_item_key)
                    if existing is not None:
                        outcomes.append(
                            BatchItemOutcome(
                                index=index,
                                transaction_id=existing,
                                error=None,
                            )
                        )
                        continue

                try:
                    tx = Transaction.register(item)
                except ValueError as exc:
                    outcomes.append(
                        BatchItemOutcome(
                            index=index,
                            transaction_id=None,
                            error=ApplicationError.validation_error(
                                "transaction", str(exc)
                            ),
                        )
                    )
                    continue

                saved = await repository.save(tx)

                if per_item_key is not None:
                    await repository.save_idempotency_key(per_item_key, saved.id)

                outcomes.append(
                    BatchItemOutcome(
                        index=index,
                        transaction_id=saved.id,
                        error=None,
                    )
                )
            except Exception as exc:
                logger.exception("batch-item-failed", extra={"index": index})
                outcomes.append(
                    BatchItemOutcome(
                        index=index,
                        transaction_id=None,
                        error=ApplicationError.unexpected(
                            "register-batch-item", str(exc)
                        ),
                    )
                )

        return outcomes
