from __future__ import annotations

from shared_contracts.alerts.v1 import AlertResolvedV1
from shared_contracts.constants import ALERTS_RESOLVED_V1

from alert.application.internal.outboundservices.messaging.message_publisher import (
    MessagePublisher,
)
from alert.domain.model.events.alert_resolved_event import AlertResolvedEvent


class AlertResolvedEventHandler:
    """Translates the internal ``AlertResolvedEvent`` into the integration
    contract ``AlertResolvedV1``. The ``new_status`` is RESOLVED or
    DISMISSED (same channel, downstream filters by field)."""

    def __init__(self, publisher: MessagePublisher) -> None:
        self._publisher = publisher

    async def on_alert_resolved(self, event: AlertResolvedEvent) -> None:
        payload = AlertResolvedV1(
            alert_id=event.alert_id,
            transaction_id=event.transaction_id,
            previous_status=event.previous_status,
            new_status=event.new_status,
            analyst_id=event.analyst_id,
            reason=event.reason,
            closed_at=event.closed_at,
        )
        await self._publisher.publish(
            channel=ALERTS_RESOLVED_V1,
            key=str(event.alert_id),
            message_type="AlertResolved",
            schema_version=1,
            payload=payload,
        )
