from __future__ import annotations

from transaction.domain.model.aggregates.transaction import Transaction
from transaction.domain.model.valueobjects.account_id import AccountId
from transaction.domain.model.valueobjects.channel import Channel
from transaction.domain.model.valueobjects.money import Money
from transaction.infrastructure.persistence.entities.transaction_persistence_entity import (
    TransactionPersistenceEntity,
)


class TransactionPersistenceAssembler:
    """
    Maps between the SQLAlchemy entity and the domain aggregate. The
    ``AccountId`` stored in the DB is a one-way SHA-256 hash, so the
    aggregate reconstructed via ``restore`` carries the hash as its value.
    """

    @staticmethod
    def to_domain(entity: TransactionPersistenceEntity) -> Transaction:
        return Transaction.restore(
            id=entity.id,
            account_id=AccountId(entity.account_id_hash),
            amount=Money(entity.amount, entity.currency),
            channel=Channel(entity.channel),
            occurred_at=entity.occurred_at,
            device_id=entity.device_id,
        )

    @staticmethod
    def to_persistence(tx: Transaction) -> TransactionPersistenceEntity:
        return TransactionPersistenceEntity(
            id=tx.id,
            account_id_hash=tx.account_id.hashed(),
            amount=tx.amount.amount,
            currency=tx.amount.currency,
            channel=tx.channel.value,
            device_id=tx.device_id,
            occurred_at=tx.occurred_at,
        )
