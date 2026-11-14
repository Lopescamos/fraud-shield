from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from analytics.domain.model.valueobjects.alert_status import AlertStatus
from analytics.domain.model.valueobjects.decision import Decision
from analytics.domain.model.valueobjects.priority import Priority
from analytics.domain.model.views.alert_view import AlertView
from analytics.domain.model.views.transaction_view import TransactionView


class FakeProjectionRepository:
    def __init__(self) -> None:
        self.transactions: dict[UUID, TransactionView] = {}
        self.alerts: dict[UUID, AlertView] = {}

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
        existing = self.transactions.get(transaction_id)
        self.transactions[transaction_id] = TransactionView(
            transaction_id=transaction_id,
            account_id_hash=account_id_hash,
            amount=amount,
            currency=currency,
            channel=channel,
            country=country,
            device_id=device_id,
            occurred_at=occurred_at,
            received_at=received_at,
            risk_score=existing.risk_score if existing else None,
            level=existing.level if existing else None,
            decision=existing.decision if existing else None,
            model_version=existing.model_version if existing else None,
            degraded_mode=existing.degraded_mode if existing else None,
            scored_at=existing.scored_at if existing else None,
        )

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
        existing = self.transactions.get(transaction_id)
        if existing is None:
            # Scored arrived before received: start a thin row that the
            # received projection will complete later.
            self.transactions[transaction_id] = TransactionView(
                transaction_id=transaction_id,
                account_id_hash=account_id_hash,
                amount=Decimal("0"),
                currency="PEN",
                channel="",
                country=None,
                device_id=None,
                occurred_at=scored_at,
                received_at=scored_at,
                risk_score=risk_score,
                level=level,
                decision=Decision(decision),
                model_version=model_version,
                degraded_mode=degraded_mode,
                scored_at=scored_at,
            )
            return
        self.transactions[transaction_id] = TransactionView(
            transaction_id=existing.transaction_id,
            account_id_hash=existing.account_id_hash,
            amount=existing.amount,
            currency=existing.currency,
            channel=existing.channel,
            country=existing.country,
            device_id=existing.device_id,
            occurred_at=existing.occurred_at,
            received_at=existing.received_at,
            risk_score=risk_score,
            level=level,
            decision=Decision(decision),
            model_version=model_version,
            degraded_mode=degraded_mode,
            scored_at=scored_at,
        )

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
        existing = self.alerts.get(alert_id)
        self.alerts[alert_id] = AlertView(
            alert_id=alert_id,
            transaction_id=transaction_id,
            account_id_hash=account_id_hash,
            priority=Priority(severity),
            score=score,
            level=level,
            status=existing.status if existing else AlertStatus.OPEN,
            opened_at=opened_at,
            analyst_id=existing.analyst_id if existing else None,
            resolution=existing.resolution if existing else None,
            closed_at=existing.closed_at if existing else None,
        )

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
        existing = self.alerts.get(alert_id)
        if existing is None:
            # Resolved arrived before raised: just remember the close.
            self.alerts[alert_id] = AlertView(
                alert_id=alert_id,
                transaction_id=transaction_id,
                account_id_hash="",
                priority=Priority.LOW,
                score=0,
                level="LOW",
                status=AlertStatus(new_status),
                opened_at=closed_at,
                analyst_id=analyst_id,
                resolution=reason,
                closed_at=closed_at,
            )
            return
        self.alerts[alert_id] = AlertView(
            alert_id=existing.alert_id,
            transaction_id=existing.transaction_id,
            account_id_hash=existing.account_id_hash,
            priority=existing.priority,
            score=existing.score,
            level=existing.level,
            status=AlertStatus(new_status),
            opened_at=existing.opened_at,
            analyst_id=analyst_id,
            resolution=reason,
            closed_at=closed_at,
        )
