from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from alert.domain.model.commands.raise_alert_from_score_command import (
    RaiseAlertFromScoreCommand,
)
from alert.domain.model.errors import InvalidAlertTransition
from alert.domain.model.events.alert_raised_event import AlertRaisedEvent
from alert.domain.model.events.alert_resolved_event import AlertResolvedEvent
from alert.domain.model.valueobjects.alert_status import AlertStatus
from alert.domain.model.valueobjects.priority import Priority
from alert.domain.model.valueobjects.risk_factor import RiskFactor
from alert.kernel.domain import AbstractDomainAggregateRoot
from alert.kernel.ids import Ids


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Alert(AbstractDomainAggregateRoot):
    id: UUID
    transaction_id: UUID
    scoring_result_id: UUID
    account_id_hash: str
    risk_score: int
    level: str
    decision: str
    model_version: str
    priority: Priority
    status: AlertStatus
    factors: list[RiskFactor] = field(default_factory=list)
    analyst_id: UUID | None = None
    resolution: str | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None

    # ---------- factory / restore ----------
    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        transaction_id: UUID,
        scoring_result_id: UUID,
        account_id_hash: str,
        risk_score: int,
        level: str,
        decision: str,
        model_version: str,
        priority: Priority,
        status: AlertStatus,
        factors: list[RiskFactor],
        analyst_id: UUID | None,
        resolution: str | None,
        opened_at: datetime | None,
        closed_at: datetime | None,
    ) -> Alert:
        return cls(
            id=id,
            transaction_id=transaction_id,
            scoring_result_id=scoring_result_id,
            account_id_hash=account_id_hash,
            risk_score=risk_score,
            level=level,
            decision=decision,
            model_version=model_version,
            priority=priority,
            status=status,
            factors=list(factors),
            analyst_id=analyst_id,
            resolution=resolution,
            opened_at=opened_at,
            closed_at=closed_at,
        )

    @classmethod
    def register(cls, command: RaiseAlertFromScoreCommand) -> Alert:
        if command.decision not in {"BLOCK", "REVIEW"}:
            raise ValueError(
                "[Alert.register] decision must be BLOCK or REVIEW to open an alert"
            )
        priority = Priority.from_risk_score(command.risk_score)
        opened_at = _now()
        alert = cls(
            id=Ids.new_id(),
            transaction_id=command.transaction_id,
            scoring_result_id=command.scoring_result_id,
            account_id_hash=command.account_id_hash,
            risk_score=command.risk_score,
            level=command.level,
            decision=command.decision,
            model_version=command.model_version,
            priority=priority,
            status=AlertStatus.OPEN,
            factors=list(command.factors),
            opened_at=opened_at,
        )
        alert._register_event(
            AlertRaisedEvent(
                alert_id=alert.id,
                transaction_id=alert.transaction_id,
                account_id_hash=alert.account_id_hash,
                severity=priority.value,
                score=alert.risk_score,
                level=alert.level,
                opened_at=opened_at,
            )
        )
        return alert

    # ---------- transitions ----------
    def assign(self, analyst_id: UUID) -> None:
        if self.status is not AlertStatus.OPEN:
            raise InvalidAlertTransition(
                current=self.status.value,
                attempted="IN_REVIEW",
                reason="alert can only be assigned while OPEN",
            )
        self.status = AlertStatus.IN_REVIEW
        self.analyst_id = analyst_id

    def resolve(self, resolution_notes: str) -> None:
        self._close(
            new_status=AlertStatus.RESOLVED,
            reason=resolution_notes,
            field_name="resolution_notes",
        )

    def dismiss(self, reason: str) -> None:
        self._close(
            new_status=AlertStatus.DISMISSED,
            reason=reason,
            field_name="reason",
        )

    def _close(
        self, *, new_status: AlertStatus, reason: str, field_name: str
    ) -> None:
        if self.status is not AlertStatus.IN_REVIEW:
            raise InvalidAlertTransition(
                current=self.status.value,
                attempted=new_status.value,
                reason=f"alert must be IN_REVIEW to be {new_status.value.lower()}",
            )
        if not reason or not reason.strip():
            raise ValueError(f"[Alert] {field_name} cannot be empty")
        previous = self.status
        self.status = new_status
        self.resolution = reason
        self.closed_at = _now()
        # analyst_id is guaranteed to be set because IN_REVIEW is reached
        # only through assign(); keep the assertion loud for the type checker.
        assert self.analyst_id is not None, "IN_REVIEW alert has no analyst"
        self._register_event(
            AlertResolvedEvent(
                alert_id=self.id,
                transaction_id=self.transaction_id,
                previous_status=previous.value,
                new_status=new_status.value,
                analyst_id=self.analyst_id,
                reason=reason,
                closed_at=self.closed_at,
            )
        )
