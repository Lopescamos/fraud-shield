from __future__ import annotations

from transaction.domain.model.commands.register_batch_transactions_command import (
    RegisterBatchTransactionsCommand,
)
from transaction.interfaces.rest.resources.register_batch_transactions_resource import (
    RegisterBatchTransactionsResource,
)
from transaction.interfaces.rest.transform.register_transaction_command_from_resource_assembler import (
    RegisterTransactionCommandFromResourceAssembler,
)


class RegisterBatchCommandFromResourceAssembler:
    @staticmethod
    def to_command(
        resource: RegisterBatchTransactionsResource,
    ) -> RegisterBatchTransactionsCommand:
        return RegisterBatchTransactionsCommand(
            items=[
                RegisterTransactionCommandFromResourceAssembler.to_command(item)
                for item in resource.items
            ],
        )
