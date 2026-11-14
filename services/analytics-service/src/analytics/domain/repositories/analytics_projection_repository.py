from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


class AnalyticsProjectionRepository(Protocol):
    """
    Write side of the projection store. All methods are UPSERTs keyed by
    the business id (``transaction_id`` / ``alert_id``), so the order of
    projection events does not matter and retries are safe. Each method
    runs inside the same session as the ``IdempotentExecutor`` marker.
    """

    async def upsert_transaction_received(
        self,
        *,
        transaction_id: UUID,
        account_id_hash: str,
        amount: Decimal,
        currency: str,
        channel: str,
        country: str | None,
        device_id: str | None,
        occurred_at: datetime,
        received_at: datetime,
    ) -> None: ...

    async def upsert_transaction_scored(
        self,
        *,
        transaction_id: UUID,
        account_id_hash: str,
        risk_score: int,
        level: str,
        decision: str,
        model_version: str,
        degraded_mode: bool,
        scored_at: datetime,
    ) -> None: ...

    async def upsert_alert_raised(
        self,
        *,
        alert_id: UUID,
        transaction_id: UUID,
        account_id_hash: str,
        severity: str,
        score: int,
        level: str,
        opened_at: datetime,
    ) -> None: ...

    async def upsert_alert_resolved(
        self,
        *,
        alert_id: UUID,
        transaction_id: UUID,
        previous_status: str,
        new_status: str,
        analyst_id: UUID,
        reason: str | None,
        closed_at: datetime,
    ) -> None: ...
