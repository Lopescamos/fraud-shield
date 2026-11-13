from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest

from alert.application.internal.commandservices.alert_application_service_impl import (
    AlertApplicationServiceImpl,
)
from alert.domain.model.commands.assign_alert_command import AssignAlertCommand
from alert.domain.model.commands.dismiss_alert_command import DismissAlertCommand
from alert.domain.model.commands.raise_alert_from_score_command import (
    RaiseAlertFromScoreCommand,
)
from alert.domain.model.commands.resolve_alert_command import ResolveAlertCommand
from alert.domain.model.valueobjects.alert_status import AlertStatus
from alert.kernel.application.result import Failure, Success
from tests.unit.application.fakes.fake_alert_repository import FakeAlertRepository
from tests.unit.application.fakes.fake_session import (
    FakeSession,
    repo_builder,
    session_factory_with,
)


def _service(
    *, repo: FakeAlertRepository, session: FakeSession
) -> AlertApplicationServiceImpl:
    return AlertApplicationServiceImpl(
        session_factory=session_factory_with(session),
        repository_builder=repo_builder(repo),
    )


@pytest.mark.asyncio
async def test_raise_from_score_creates_alert_in_open(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    repo = FakeAlertRepository()
    session = FakeSession()
    service = _service(repo=repo, session=session)

    result = await service.raise_from_score(sample_raise_command)

    assert isinstance(result, Success)
    assert result.value is not None
    stored = await repo.find_by_id(result.value)
    assert stored is not None
    assert stored.status is AlertStatus.OPEN
    assert len(repo.published_events) == 1


@pytest.mark.asyncio
async def test_raise_from_score_is_noop_for_approve(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    repo = FakeAlertRepository()
    service = _service(repo=repo, session=FakeSession())

    cmd = replace(sample_raise_command, decision="APPROVE")
    result = await service.raise_from_score(cmd)

    assert isinstance(result, Success)
    assert result.value is None
    assert repo.published_events == []


@pytest.mark.asyncio
async def test_raise_from_score_is_idempotent_by_transaction_id(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    repo = FakeAlertRepository()

    first = await _service(repo=repo, session=FakeSession()).raise_from_score(
        sample_raise_command
    )
    assert isinstance(first, Success)
    assert first.value is not None

    second = await _service(repo=repo, session=FakeSession()).raise_from_score(
        sample_raise_command
    )
    assert isinstance(second, Success)
    assert second.value == first.value
    assert len(repo.published_events) == 1


@pytest.mark.asyncio
async def test_assign_moves_open_to_in_review(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    repo = FakeAlertRepository()
    service = _service(repo=repo, session=FakeSession())

    raised = await service.raise_from_score(sample_raise_command)
    assert isinstance(raised, Success)
    alert_id = raised.value
    assert alert_id is not None

    analyst = uuid4()
    assigned = await _service(repo=repo, session=FakeSession()).assign(
        AssignAlertCommand(alert_id=alert_id, analyst_id=analyst)
    )

    assert isinstance(assigned, Success)
    stored = await repo.find_by_id(alert_id)
    assert stored is not None
    assert stored.status is AlertStatus.IN_REVIEW
    assert stored.analyst_id == analyst


@pytest.mark.asyncio
async def test_resolve_from_open_returns_business_rule_violation(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    repo = FakeAlertRepository()
    service = _service(repo=repo, session=FakeSession())
    raised = await service.raise_from_score(sample_raise_command)
    assert isinstance(raised, Success)
    assert raised.value is not None

    session = FakeSession()
    resolve = await _service(repo=repo, session=session).resolve(
        ResolveAlertCommand(alert_id=raised.value, resolution_notes="fraud")
    )

    assert isinstance(resolve, Failure)
    assert resolve.error.code == "business_rule_violation"
    assert session.trans.rolled_back is True


@pytest.mark.asyncio
async def test_resolve_from_in_review_succeeds_and_emits_event(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    repo = FakeAlertRepository()
    raised = await _service(repo=repo, session=FakeSession()).raise_from_score(
        sample_raise_command
    )
    assert isinstance(raised, Success)
    assert raised.value is not None

    await _service(repo=repo, session=FakeSession()).assign(
        AssignAlertCommand(alert_id=raised.value, analyst_id=uuid4())
    )
    repo.published_events.clear()

    resolve = await _service(repo=repo, session=FakeSession()).resolve(
        ResolveAlertCommand(alert_id=raised.value, resolution_notes="confirmed")
    )

    assert isinstance(resolve, Success)
    stored = await repo.find_by_id(raised.value)
    assert stored is not None
    assert stored.status is AlertStatus.RESOLVED
    assert len(repo.published_events) == 1
    assert repo.published_events[0].new_status == "RESOLVED"


@pytest.mark.asyncio
async def test_dismiss_from_in_review_succeeds(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    repo = FakeAlertRepository()
    raised = await _service(repo=repo, session=FakeSession()).raise_from_score(
        sample_raise_command
    )
    assert isinstance(raised, Success)
    assert raised.value is not None

    await _service(repo=repo, session=FakeSession()).assign(
        AssignAlertCommand(alert_id=raised.value, analyst_id=uuid4())
    )

    dismiss = await _service(repo=repo, session=FakeSession()).dismiss(
        DismissAlertCommand(alert_id=raised.value, reason="false positive")
    )

    assert isinstance(dismiss, Success)
    stored = await repo.find_by_id(raised.value)
    assert stored is not None
    assert stored.status is AlertStatus.DISMISSED


@pytest.mark.asyncio
async def test_resolve_with_empty_notes_returns_validation_error(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    repo = FakeAlertRepository()
    raised = await _service(repo=repo, session=FakeSession()).raise_from_score(
        sample_raise_command
    )
    assert isinstance(raised, Success)
    assert raised.value is not None
    await _service(repo=repo, session=FakeSession()).assign(
        AssignAlertCommand(alert_id=raised.value, analyst_id=uuid4())
    )

    result = await _service(repo=repo, session=FakeSession()).resolve(
        ResolveAlertCommand(alert_id=raised.value, resolution_notes="  ")
    )

    assert isinstance(result, Failure)
    assert result.error.code == "validation_error"


@pytest.mark.asyncio
async def test_assign_missing_alert_returns_not_found() -> None:
    repo = FakeAlertRepository()
    result = await _service(repo=repo, session=FakeSession()).assign(
        AssignAlertCommand(alert_id=uuid4(), analyst_id=uuid4())
    )

    assert isinstance(result, Failure)
    assert result.error.code == "not_found"


@pytest.mark.asyncio
async def test_rollback_on_repo_save_failure(
    sample_raise_command: RaiseAlertFromScoreCommand,
) -> None:
    class FailingRepo(FakeAlertRepository):
        async def save(self, alert):  # type: ignore[override]
            raise RuntimeError("db-down")

    session = FakeSession()
    service = _service(repo=FailingRepo(), session=session)

    result = await service.raise_from_score(sample_raise_command)

    assert isinstance(result, Failure)
    assert result.error.code == "unexpected"
    assert session.trans.rolled_back is True
