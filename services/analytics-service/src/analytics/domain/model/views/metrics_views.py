from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class DailyMetric:
    day: date
    transactions: int
    alerts: int
    blocked: int
    fraud_rate: float
    priority_low: int
    priority_medium: int
    priority_high: int
    priority_critical: int


@dataclass(frozen=True, slots=True)
class SummaryMetric:
    total_transactions: int
    total_alerts: int
    open_alerts: int
    in_review_alerts: int
    resolved_alerts: int
    dismissed_alerts: int
    blocked_transactions: int
    review_transactions: int
    fraud_rate: float
