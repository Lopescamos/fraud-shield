from __future__ import annotations

from shared_contracts.alerts.v1 import AlertRaisedV1
from shared_contracts.constants import ALERTS_RAISED_V1

from alert.application.internal.outboundservices.messaging.message_publisher import (
    MessagePublisher,
)
from alert.domain.model.events.alert_raised_event import AlertRaisedEvent


class AlertRaisedEventHandler:
    """Boundary between the domain event and the integration contract
    ``AlertRaisedV1``. Single application piece allowed to import
    ``shared_contracts``."""

    def __init__(self, publisher: MessagePublisher) -> None:
        self._publisher = publisher

    async def on_alert_raised(self, event: AlertRaisedEvent) -> None:
        payload = AlertRaisedV1(
            alert_id=event.alert_id,
            transaction_id=event.transaction_id,
            account_id_hash=event.account_id_hash,
            severity=event.severity,
            score=event.score,
            level=event.level,
            opened_at=event.opened_at,
        )
        await self._publisher.publish(
            channel=ALERTS_RAISED_V1,
            key=str(event.alert_id),
            message_type="AlertRaised",
            schema_version=1,
            payload=payload,
        )
