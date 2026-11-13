from __future__ import annotations

from uuid import uuid4

import pytest

from alert.domain.model.aggregates.alert import Alert
from alert.domain.model.commands.raise_alert_from_score_command import (
    RaiseAlertFromScoreCommand,
)
from alert.domain.model.errors import InvalidAlertTransition
from alert.domain.model.events.alert_raised_event import AlertRaisedEvent
from alert.domain.model.events.alert_resolved_event import AlertResolvedEvent
from alert.domain.model.valueobjects.alert_status import AlertStatus
from alert.domain.model.valueobjects.priority import Priority


def test_register_opens_alert_and_emits_event(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    alert = Alert.register(sample_raise_command)

    assert alert.id is not None
    assert alert.status is AlertStatus.OPEN
    assert alert.priority is Priority.HIGH  # 78 >= 75
    assert alert.analyst_id is None
    assert alert.closed_at is None
    assert alert.opened_at is not None

    events = alert.pull_events()
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, AlertRaisedEvent)
    assert event.alert_id == alert.id
    assert event.transaction_id == alert.transaction_id
    assert event.severity == "HIGH"
    assert event.score == 78


@pytest.mark.parametrize("decision", ["APPROVE", "", "SOMETHING"])
def test_register_rejects_non_blocking_decisions(decision: str) -> None:
    cmd = RaiseAlertFromScoreCommand(
        transaction_id=uuid4(),
        scoring_result_id=uuid4(),
        account_id_hash="a" * 64,
        risk_score=50,
        level="MEDIUM",
        decision=decision,
        model_version="v1",
        scored_at=__import__("datetime").datetime.now(
            __import__("datetime").UTC
        ),
    )
    with pytest.raises(ValueError, match="BLOCK or REVIEW"):
        Alert.register(cmd)


def test_assign_moves_open_to_in_review(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    alert = Alert.register(sample_raise_command)
    _ = alert.pull_events()
    analyst = uuid4()

    alert.assign(analyst)

    assert alert.status is AlertStatus.IN_REVIEW
    assert alert.analyst_id == analyst
    assert alert.pull_events() == []


def test_assign_rejects_non_open_states(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    alert = Alert.register(sample_raise_command)
    alert.assign(uuid4())

    with pytest.raises(InvalidAlertTransition) as info:
        alert.assign(uuid4())
    assert info.value.current == "IN_REVIEW"
    assert info.value.attempted == "IN_REVIEW"


def test_resolve_moves_in_review_to_resolved_and_emits_event(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    alert = Alert.register(sample_raise_command)
    analyst = uuid4()
    alert.assign(analyst)
    _ = alert.pull_events()

    alert.resolve("confirmed fraud, card cancelled")

    assert alert.status is AlertStatus.RESOLVED
    assert alert.resolution == "confirmed fraud, card cancelled"
    assert alert.closed_at is not None

    events = alert.pull_events()
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, AlertResolvedEvent)
    assert event.previous_status == "IN_REVIEW"
    assert event.new_status == "RESOLVED"
    assert event.analyst_id == analyst
    assert event.reason == "confirmed fraud, card cancelled"


def test_dismiss_moves_in_review_to_dismissed_and_emits_event(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    alert = Alert.register(sample_raise_command)
    alert.assign(uuid4())
    _ = alert.pull_events()

    alert.dismiss("false positive, legitimate purchase")

    assert alert.status is AlertStatus.DISMISSED
    event = alert.pull_events()[0]
    assert isinstance(event, AlertResolvedEvent)
    assert event.new_status == "DISMISSED"
    assert event.reason == "false positive, legitimate purchase"


def test_resolve_from_open_is_rejected(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    alert = Alert.register(sample_raise_command)

    with pytest.raises(InvalidAlertTransition) as info:
        alert.resolve("notes")
    assert info.value.current == "OPEN"
    assert info.value.attempted == "RESOLVED"


def test_dismiss_from_open_is_rejected(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    alert = Alert.register(sample_raise_command)

    with pytest.raises(InvalidAlertTransition):
        alert.dismiss("some reason")


def test_resolve_rejects_empty_notes(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    alert = Alert.register(sample_raise_command)
    alert.assign(uuid4())

    with pytest.raises(ValueError, match="resolution_notes"):
        alert.resolve("   ")


def test_dismiss_rejects_empty_reason(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    alert = Alert.register(sample_raise_command)
    alert.assign(uuid4())

    with pytest.raises(ValueError, match="reason"):
        alert.dismiss("")


def test_cannot_reassign_after_resolved(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    alert = Alert.register(sample_raise_command)
    alert.assign(uuid4())
    alert.resolve("done")

    with pytest.raises(InvalidAlertTransition):
        alert.resolve("do it again")


def test_restore_does_not_emit_events(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    source = Alert.register(sample_raise_command)
    _ = source.pull_events()

    rebuilt = Alert.restore(
        id=source.id,
        transaction_id=source.transaction_id,
        scoring_result_id=source.scoring_result_id,
        account_id_hash=source.account_id_hash,
        risk_score=source.risk_score,
        level=source.level,
        decision=source.decision,
        model_version=source.model_version,
        priority=source.priority,
        status=AlertStatus.IN_REVIEW,
        factors=source.factors,
        analyst_id=uuid4(),
        resolution=None,
        opened_at=source.opened_at,
        closed_at=None,
    )
    assert rebuilt.pull_events() == []
