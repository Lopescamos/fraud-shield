from __future__ import annotations

from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.interfaces.rest.resources.score_transaction_resource import (
    ScoreTransactionResource,
)


class ScoreTransactionCommandFromResourceAssembler:
    @staticmethod
    def to_command(resource: ScoreTransactionResource) -> ScoreTransactionCommand:
        return ScoreTransactionCommand(
            transaction_id=resource.transaction_id,
            account_id_hash=resource.account_id_hash,
            amount=resource.amount,
            currency=resource.currency,
            channel=resource.channel,
            occurred_at=resource.occurred_at,
            country=resource.country,
            device_id=resource.device_id,
            extra_features=dict(resource.extra_features),
        )
