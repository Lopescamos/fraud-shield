from __future__ import annotations

from shared_contracts.constants import TRANSACTIONS_SCORED_V1
from shared_contracts.transactions.v1 import TransactionScoredV1

from scoring.application.internal.outboundservices.messaging.message_publisher import (
    MessagePublisher,
)
from scoring.domain.model.events.scoring_result_registered_event import (
    ScoringResultRegisteredEvent,
)


class ScoringResultRegisteredEventHandler:
    """
    Boundary between the domain event and the integration contract
    ``TransactionScoredV1``. Single application piece allowed to import
    ``shared_contracts``.
    """

    def __init__(self, publisher: MessagePublisher) -> None:
        self._publisher = publisher

    async def on_scoring_result_registered(
        self, event: ScoringResultRegisteredEvent
    ) -> None:
        payload = TransactionScoredV1(
            assessment_id=event.scoring_result_id,
            transaction_id=event.transaction_id,
            account_id_hash=event.account_id_hash,
            score=event.score,
            level=event.level,
            rules_score=event.rules_score,
            xgb_probability=event.xgb_probability,
            iforest_anomaly=event.iforest_anomaly,
            degraded_mode=event.degraded_mode,
            model_version=event.model_version,
            occurred_at=event.occurred_at,
        )
        await self._publisher.publish(
            channel=TRANSACTIONS_SCORED_V1,
            key=event.account_id_hash,
            message_type="TransactionScored",
            schema_version=1,
            payload=payload,
        )
