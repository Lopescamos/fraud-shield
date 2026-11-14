from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from analytics.domain.model.valueobjects.alert_status import AlertStatus
from analytics.domain.model.valueobjects.decision import Decision
from analytics.domain.model.valueobjects.priority import Priority
from analytics.domain.model.views.alert_view import AlertView
from analytics.domain.model.views.metrics_views import DailyMetric, SummaryMetric
from analytics.domain.model.views.transaction_view import TransactionView


def test_transaction_view_defaults_scoring_fields_to_none() -> None:
    view = TransactionView(
        transaction_id=uuid4(),
        account_id_hash="a" * 64,
        amount=Decimal("250.00"),
        currency="PEN",
        channel="WEB",
        country="PE",
        device_id="d-1",
        occurred_at=datetime(2026, 11, 14, tzinfo=UTC),
        received_at=datetime(2026, 11, 14, tzinfo=UTC),
    )
    assert view.risk_score is None
    assert view.decision is None
    assert view.model_version is None


def test_transaction_view_carries_scoring_fields() -> None:
    view = TransactionView(
        transaction_id=uuid4(),
        account_id_hash="a" * 64,
        amount=Decimal("250.00"),
        currency="PEN",
        channel="WEB",
        country="PE",
        device_id=None,
        occurred_at=datetime(2026, 11, 14, tzinfo=UTC),
        received_at=datetime(2026, 11, 14, tzinfo=UTC),
        risk_score=80,
        level="HIGH",
        decision=Decision.REVIEW,
        model_version="xgb-v1",
        degraded_mode=False,
        scored_at=datetime(2026, 11, 14, 1, tzinfo=UTC),
    )
    assert view.decision is Decision.REVIEW


def test_alert_view_defaults_closed_fields_to_none() -> None:
    view = AlertView(
        alert_id=uuid4(),
        transaction_id=uuid4(),
        account_id_hash="b" * 64,
        priority=Priority.CRITICAL,
        score=95,
        level="CRITICAL",
        status=AlertStatus.OPEN,
        opened_at=datetime(2026, 11, 14, tzinfo=UTC),
    )
    assert view.analyst_id is None
    assert view.closed_at is None
    assert view.resolution is None


def test_daily_metric_exposes_all_priority_buckets() -> None:
    metric = DailyMetric(
        day=datetime(2026, 11, 14).date(),
        transactions=100,
        alerts=10,
        blocked=2,
        fraud_rate=0.1,
        priority_low=5,
        priority_medium=3,
        priority_high=1,
        priority_critical=1,
    )
    assert (
        metric.priority_low
        + metric.priority_medium
        + metric.priority_high
        + metric.priority_critical
        == metric.alerts
    )


def test_summary_metric_is_flat() -> None:
    summary = SummaryMetric(
        total_transactions=1_000,
        total_alerts=50,
        open_alerts=10,
        in_review_alerts=5,
        resolved_alerts=25,
        dismissed_alerts=10,
        blocked_transactions=20,
        review_transactions=30,
        fraud_rate=0.05,
    )
    assert summary.total_alerts == 50
