from __future__ import annotations

from transaction.domain.model.aggregates.transaction import Transaction
from transaction.interfaces.rest.resources.transaction_resource import (
    TransactionResource,
)


class TransactionResourceFromEntityAssembler:
    @staticmethod
    def to_resource(tx: Transaction) -> TransactionResource:
        return TransactionResource(
            transaction_id=tx.id,
            account_id_hash=tx.account_id.hashed(),
            amount=tx.amount.amount,
            currency=tx.amount.currency,
            channel=tx.channel.value,
            occurred_at=tx.occurred_at,
            device_id=tx.device_id,
        )
