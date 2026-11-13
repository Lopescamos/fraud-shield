from __future__ import annotations

from transaction.domain.model.commands.register_transaction_command import (
    RegisterTransactionCommand,
)
from transaction.interfaces.rest.resources.register_transaction_resource import (
    RegisterTransactionResource,
)


class RegisterTransactionCommandFromResourceAssembler:
    @staticmethod
    def to_command(
        resource: RegisterTransactionResource,
    ) -> RegisterTransactionCommand:
        return RegisterTransactionCommand(
            account_id=resource.account_id,
            amount=resource.amount,
            currency=resource.currency,
            channel=resource.channel,
            occurred_at=resource.occurred_at,
            device_id=resource.device_id,
        )
