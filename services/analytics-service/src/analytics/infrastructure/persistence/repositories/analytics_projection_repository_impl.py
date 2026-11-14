from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.domain.repositories.analytics_projection_repository import (
    AnalyticsProjectionRepository,
)
from analytics.infrastructure.persistence.entities.alert_view_entity import (
    AlertViewEntity,
)
from analytics.infrastructure.persistence.entities.transaction_view_entity import (
    TransactionViewEntity,
)


class AnalyticsProjectionRepositoryImpl(AnalyticsProjectionRepository):
    """
    Projection writer. Each method uses ``INSERT ... ON CONFLICT DO
    UPDATE`` keyed by the business id so the projectors can arrive in
    any order (scored before received, resolved before raised) without
    losing the data that is already there.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
    ) -> None:
        stmt = (
            insert(TransactionViewEntity)
            .values(
                transaction_id=transaction_id,
                account_id_hash=account_id_hash,
                amount=amount,
                currency=currency,
                channel=channel,
                country=country,
                device_id=device_id,
                occurred_at=occurred_at,
                received_at=received_at,
            )
            .on_conflict_do_update(
                index_elements=[TransactionViewEntity.transaction_id],
                set_={
                    "account_id_hash": account_id_hash,
                    "amount": amount,
                    "currency": currency,
                    "channel": channel,
                    "country": country,
                    "device_id": device_id,
                    "occurred_at": occurred_at,
                    "received_at": received_at,
                },
            )
        )
        await self._session.execute(stmt)

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
    ) -> None:
        stmt = (
            insert(TransactionViewEntity)
            .values(
                transaction_id=transaction_id,
                account_id_hash=account_id_hash,
                # Placeholder values used only if the scored event arrives
                # before received; they are overwritten by the next upsert.
                amount=Decimal("0"),
                currency="",
                channel="",
                occurred_at=scored_at,
                received_at=scored_at,
                risk_score=risk_score,
                level=level,
                decision=decision,
                model_version=model_version,
                degraded_mode=degraded_mode,
                scored_at=scored_at,
            )
            .on_conflict_do_update(
                index_elements=[TransactionViewEntity.transaction_id],
                set_={
                    "risk_score": risk_score,
                    "level": level,
                    "decision": decision,
                    "model_version": model_version,
                    "degraded_mode": degraded_mode,
                    "scored_at": scored_at,
                },
            )
        )
        await self._session.execute(stmt)

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
    ) -> None:
        stmt = (
            insert(AlertViewEntity)
            .values(
                alert_id=alert_id,
                transaction_id=transaction_id,
                account_id_hash=account_id_hash,
                priority=severity,
                score=score,
                level=level,
                status="OPEN",
                opened_at=opened_at,
            )
            .on_conflict_do_update(
                index_elements=[AlertViewEntity.alert_id],
                set_={
                    "transaction_id": transaction_id,
                    "account_id_hash": account_id_hash,
                    "priority": severity,
                    "score": score,
                    "level": level,
                    "opened_at": opened_at,
                },
            )
        )
        await self._session.execute(stmt)

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
    ) -> None:
        stmt = (
            insert(AlertViewEntity)
            .values(
                alert_id=alert_id,
                transaction_id=transaction_id,
                # Defaults for the resolved-before-raised case. They are
                # overwritten when (and if) the raise projection arrives.
                account_id_hash="",
                priority="LOW",
                score=0,
                level="LOW",
                status=new_status,
                opened_at=closed_at,
                analyst_id=analyst_id,
                resolution=reason,
                closed_at=closed_at,
            )
            .on_conflict_do_update(
                index_elements=[AlertViewEntity.alert_id],
                set_={
                    "status": new_status,
                    "analyst_id": analyst_id,
                    "resolution": reason,
                    "closed_at": closed_at,
                },
            )
        )
        await self._session.execute(stmt)
