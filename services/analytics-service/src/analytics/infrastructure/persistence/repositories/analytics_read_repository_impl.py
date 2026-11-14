from __future__ import annotations

from sqlalchemy import case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from analytics.domain.model.queries.daily_metrics_query import (
    GetDailyMetricsQuery,
    GetSummaryMetricsQuery,
)
from analytics.domain.model.queries.list_alerts_query import ListAlertsQuery
from analytics.domain.model.queries.list_transactions_query import (
    ListTransactionsQuery,
)
from analytics.domain.model.valueobjects.alert_status import AlertStatus
from analytics.domain.model.valueobjects.decision import Decision
from analytics.domain.model.valueobjects.priority import Priority
from analytics.domain.model.views.alert_view import AlertView
from analytics.domain.model.views.metrics_views import DailyMetric, SummaryMetric
from analytics.domain.model.views.transaction_view import TransactionView
from analytics.domain.repositories.analytics_read_repository import (
    AnalyticsReadRepository,
)
from analytics.infrastructure.persistence.entities.alert_view_entity import (
    AlertViewEntity,
)
from analytics.infrastructure.persistence.entities.transaction_view_entity import (
    TransactionViewEntity,
)


class AnalyticsReadRepositoryImpl(AnalyticsReadRepository):
    """Read side over the projected tables. ``daily_metrics`` and
    ``summary_metrics`` are computed on-the-fly with aggregated SQL so
    there is no materialized table to keep in sync."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_transactions(
        self, query: ListTransactionsQuery
    ) -> list[TransactionView]:
        stmt = select(TransactionViewEntity)
        if query.date_from is not None:
            stmt = stmt.where(TransactionViewEntity.occurred_at >= query.date_from)
        if query.date_to is not None:
            stmt = stmt.where(TransactionViewEntity.occurred_at <= query.date_to)
        if query.decision is not None:
            stmt = stmt.where(TransactionViewEntity.decision == query.decision.value)
        if query.country is not None:
            stmt = stmt.where(TransactionViewEntity.country == query.country)
        stmt = (
            stmt.order_by(TransactionViewEntity.occurred_at.desc())
            .offset(query.offset)
            .limit(query.limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_tx_entity_to_view(r) for r in rows]

    async def list_alerts(self, query: ListAlertsQuery) -> list[AlertView]:
        stmt = select(AlertViewEntity)
        if query.status is not None:
            stmt = stmt.where(AlertViewEntity.status == query.status.value)
        if query.priority is not None:
            stmt = stmt.where(AlertViewEntity.priority == query.priority.value)
        stmt = (
            stmt.order_by(AlertViewEntity.opened_at.desc())
            .offset(query.offset)
            .limit(query.limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_alert_entity_to_view(r) for r in rows]

    async def daily_metrics(
        self, query: GetDailyMetricsQuery
    ) -> list[DailyMetric]:
        day_tx = cast(TransactionViewEntity.occurred_at, Date).label("day")
        tx_stmt = (
            select(
                day_tx,
                func.count().label("transactions"),
                func.sum(
                    case((TransactionViewEntity.decision == "BLOCK", 1), else_=0)
                ).label("blocked"),
            )
            .where(TransactionViewEntity.occurred_at >= query.date_from)
            .where(TransactionViewEntity.occurred_at <= query.date_to)
            .group_by(day_tx)
        )
        tx_by_day = {
            row.day: (row.transactions, row.blocked or 0)
            for row in (await self._session.execute(tx_stmt)).all()
        }

        day_alert = cast(AlertViewEntity.opened_at, Date).label("day")
        alert_stmt = (
            select(
                day_alert,
                func.count().label("alerts"),
                func.sum(
                    case((AlertViewEntity.priority == "LOW", 1), else_=0)
                ).label("priority_low"),
                func.sum(
                    case((AlertViewEntity.priority == "MEDIUM", 1), else_=0)
                ).label("priority_medium"),
                func.sum(
                    case((AlertViewEntity.priority == "HIGH", 1), else_=0)
                ).label("priority_high"),
                func.sum(
                    case((AlertViewEntity.priority == "CRITICAL", 1), else_=0)
                ).label("priority_critical"),
            )
            .where(AlertViewEntity.opened_at >= query.date_from)
            .where(AlertViewEntity.opened_at <= query.date_to)
            .group_by(day_alert)
        )
        alerts_by_day = {
            row.day: row for row in (await self._session.execute(alert_stmt)).all()
        }

        all_days = sorted(set(tx_by_day) | set(alerts_by_day))
        metrics: list[DailyMetric] = []
        for day in all_days:
            tx_count, blocked = tx_by_day.get(day, (0, 0))
            alert_row = alerts_by_day.get(day)
            alerts = alert_row.alerts if alert_row else 0
            fraud_rate = (alerts / tx_count) if tx_count else 0.0
            metrics.append(
                DailyMetric(
                    day=day,
                    transactions=tx_count,
                    alerts=alerts,
                    blocked=int(blocked or 0),
                    fraud_rate=float(fraud_rate),
                    priority_low=int(alert_row.priority_low or 0) if alert_row else 0,
                    priority_medium=int(alert_row.priority_medium or 0)
                    if alert_row
                    else 0,
                    priority_high=int(alert_row.priority_high or 0) if alert_row else 0,
                    priority_critical=int(alert_row.priority_critical or 0)
                    if alert_row
                    else 0,
                )
            )
        return metrics

    async def summary_metrics(
        self, query: GetSummaryMetricsQuery
    ) -> SummaryMetric:
        tx_stmt = select(
            func.count().label("total"),
            func.sum(
                case((TransactionViewEntity.decision == "BLOCK", 1), else_=0)
            ).label("blocked"),
            func.sum(
                case((TransactionViewEntity.decision == "REVIEW", 1), else_=0)
            ).label("review"),
        )
        tx_row = (await self._session.execute(tx_stmt)).one()

        alert_stmt = select(
            func.count().label("total"),
            func.sum(
                case((AlertViewEntity.status == AlertStatus.OPEN.value, 1), else_=0)
            ).label("open"),
            func.sum(
                case(
                    (AlertViewEntity.status == AlertStatus.IN_REVIEW.value, 1),
                    else_=0,
                )
            ).label("in_review"),
            func.sum(
                case(
                    (AlertViewEntity.status == AlertStatus.RESOLVED.value, 1),
                    else_=0,
                )
            ).label("resolved"),
            func.sum(
                case(
                    (AlertViewEntity.status == AlertStatus.DISMISSED.value, 1),
                    else_=0,
                )
            ).label("dismissed"),
        )
        alert_row = (await self._session.execute(alert_stmt)).one()

        total_tx = tx_row.total or 0
        total_alerts = alert_row.total or 0
        fraud_rate = (total_alerts / total_tx) if total_tx else 0.0

        return SummaryMetric(
            total_transactions=total_tx,
            total_alerts=total_alerts,
            open_alerts=int(alert_row.open or 0),
            in_review_alerts=int(alert_row.in_review or 0),
            resolved_alerts=int(alert_row.resolved or 0),
            dismissed_alerts=int(alert_row.dismissed or 0),
            blocked_transactions=int(tx_row.blocked or 0),
            review_transactions=int(tx_row.review or 0),
            fraud_rate=float(fraud_rate),
        )


def _tx_entity_to_view(entity: TransactionViewEntity) -> TransactionView:
    return TransactionView(
        transaction_id=entity.transaction_id,
        account_id_hash=entity.account_id_hash,
        amount=entity.amount,
        currency=entity.currency,
        channel=entity.channel,
        country=entity.country,
        device_id=entity.device_id,
        occurred_at=entity.occurred_at,
        received_at=entity.received_at,
        risk_score=entity.risk_score,
        level=entity.level,
        decision=Decision(entity.decision) if entity.decision else None,
        model_version=entity.model_version,
        degraded_mode=entity.degraded_mode,
        scored_at=entity.scored_at,
    )


def _alert_entity_to_view(entity: AlertViewEntity) -> AlertView:
    return AlertView(
        alert_id=entity.alert_id,
        transaction_id=entity.transaction_id,
        account_id_hash=entity.account_id_hash,
        priority=Priority(entity.priority),
        score=entity.score,
        level=entity.level,
        status=AlertStatus(entity.status),
        opened_at=entity.opened_at,
        analyst_id=entity.analyst_id,
        resolution=entity.resolution,
        closed_at=entity.closed_at,
    )
