from __future__ import annotations

from typing import Protocol

from analytics.application.dto.projection_input import (
    AlertRaisedInput,
    AlertResolvedInput,
    TransactionReceivedInput,
    TransactionScoredInput,
)
from analytics.kernel.application.result import ApplicationError, Result


class ProjectionApplicationService(Protocol):
    """
    Projects the four integration events into the read tables. Each
    method is idempotent per ``(message_id, consumer_group)``: a
    duplicate delivery returns ``Success(None)`` without side effects.
    """

    async def on_transaction_received(
        self, input_: TransactionReceivedInput, consumer_group: str
    ) -> Result[None, ApplicationError]: ...

    async def on_transaction_scored(
        self, input_: TransactionScoredInput, consumer_group: str
    ) -> Result[None, ApplicationError]: ...

    async def on_alert_raised(
        self, input_: AlertRaisedInput, consumer_group: str
    ) -> Result[None, ApplicationError]: ...

    async def on_alert_resolved(
        self, input_: AlertResolvedInput, consumer_group: str
    ) -> Result[None, ApplicationError]: ...
