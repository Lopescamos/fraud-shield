from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from transaction.domain.model.commands.register_transaction_command import (
    RegisterTransactionCommand,
)
from transaction.domain.model.events.transaction_registered_event import (
    TransactionRegisteredEvent,
)
from transaction.domain.model.valueobjects.account_id import AccountId
from transaction.domain.model.valueobjects.channel import Channel
from transaction.domain.model.valueobjects.money import Money
from transaction.kernel.domain import AbstractDomainAggregateRoot
from transaction.kernel.ids import Ids


@dataclass
class Transaction(AbstractDomainAggregateRoot):
    id: UUID
    account_id: AccountId
    amount: Money
    channel: Channel
    occurred_at: datetime
    device_id: str | None = None

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        account_id: AccountId,
        amount: Money,
        channel: Channel,
        occurred_at: datetime,
        device_id: str | None = None,
    ) -> "Transaction":
        return cls(
            id=id,
            account_id=account_id,
            amount=amount,
            channel=channel,
            occurred_at=occurred_at,
            device_id=device_id,
        )

    @classmethod
    def register(cls, command: RegisterTransactionCommand) -> "Transaction":
        tx = cls(
            id=Ids.new_id(),
            account_id=AccountId(command.account_id),
            amount=Money(command.amount, command.currency),
            channel=command.channel,
            occurred_at=command.occurred_at,
            device_id=command.device_id,
        )
        tx._register_event(
            TransactionRegisteredEvent(
                transaction_id=tx.id,
                account_id_hash=tx.account_id.hashed(),
                amount=tx.amount.amount,
                currency=tx.amount.currency,
                channel=tx.channel.value,
                device_id=tx.device_id,
                occurred_at=tx.occurred_at,
            )
        )
        return tx
