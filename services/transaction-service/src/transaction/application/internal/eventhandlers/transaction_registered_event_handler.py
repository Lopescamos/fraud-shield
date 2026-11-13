from __future__ import annotations

from shared_contracts.constants import TRANSACTIONS_RECEIVED_V1
from shared_contracts.transactions.v1 import TransactionReceivedV1

from transaction.application.internal.outboundservices.messaging.message_publisher import (
    MessagePublisher,
)
from transaction.domain.model.events.transaction_registered_event import (
    TransactionRegisteredEvent,
)


class TransactionRegisteredEventHandler:
    """
    Boundary between the domain event (internal) and the integration
    contract (``TransactionReceivedV1``). This is the single application
    piece allowed to import ``shared_contracts``.
    """

    def __init__(self, publisher: MessagePublisher) -> None:
        self._publisher = publisher

    async def on_transaction_registered(
        self, event: TransactionRegisteredEvent
    ) -> None:
        payload = TransactionReceivedV1(
            transaction_id=event.transaction_id,
            account_id_hash=event.account_id_hash,
            amount=event.amount,
            currency=event.currency,
            channel=event.channel,
            device_id=event.device_id,
            occurred_at=event.occurred_at,
        )
        await self._publisher.publish(
            channel=TRANSACTIONS_RECEIVED_V1,
            key=event.account_id_hash,
            message_type="TransactionReceived",
            schema_version=1,
            payload=payload,
        )
