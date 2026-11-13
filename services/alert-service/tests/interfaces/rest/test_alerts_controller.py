from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from alert.domain.model.aggregates.alert import Alert
from alert.domain.model.commands.raise_alert_from_score_command import (
    RaiseAlertFromScoreCommand,
)
from alert.domain.model.valueobjects.alert_status import AlertStatus
from alert.domain.model.valueobjects.priority import Priority
from alert.interfaces.rest import exception_handlers
from alert.interfaces.rest.alerts_controller import router as alerts_router
from alert.interfaces.rest.health_controller import router as health_router
from alert.kernel.application.result import (
    ApplicationError,
    Failure,
    Success,
)


class FakeCommandService:
    def __init__(self) -> None:
        self.assign_calls: list = []
        self.resolve_calls: list = []
        self.dismiss_calls: list = []
        self._next_failure: ApplicationError | None = None

    def will_fail_with(self, error: ApplicationError) -> None:
        self._next_failure = error

    async def raise_from_score(self, command):
        raise NotImplementedError

    async def assign(self, command):
        self.assign_calls.append(command)
        if self._next_failure is not None:
            return Failure(self._next_failure)
        return Success(command.alert_id)

    async def resolve(self, command):
        self.resolve_calls.append(command)
        if self._next_failure is not None:
            return Failure(self._next_failure)
        return Success(command.alert_id)

    async def dismiss(self, command):
        self.dismiss_calls.append(command)
        if self._next_failure is not None:
            return Failure(self._next_failure)
        return Success(command.alert_id)


class FakeQueryService:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Alert] = {}

    def add(self, alert: Alert) -> None:
        self._by_id[alert.id] = alert

    async def get_by_id(self, query):
        return self._by_id.get(query.alert_id)

    async def list(self, query):
        items = list(self._by_id.values())
        if query.status is not None:
            items = [a for a in items if a.status is query.status]
        if query.priority is not None:
            items = [a for a in items if a.priority is query.priority]
        return items[query.offset : query.offset + query.limit]


def _build_app() -> tuple[FastAPI, FakeCommandService, FakeQueryService]:
    command = FakeCommandService()
    query = FakeQueryService()
    app = FastAPI()
    app.state.alert_application_service = command
    app.state.alert_query_service = query
    exception_handlers.register(app)
    app.include_router(health_router)
    app.include_router(alerts_router)
    return app, command, query


def _sample_alert(risk_score: int = 78) -> Alert:
    cmd = RaiseAlertFromScoreCommand(
        transaction_id=uuid4(),
        scoring_result_id=uuid4(),
        account_id_hash="a" * 64,
        risk_score=risk_score,
        level="HIGH",
        decision="REVIEW",
        model_version="xgb-v1",
        scored_at=datetime.now(UTC),
    )
    alert = Alert.register(cmd)
    _ = alert.pull_events()
    return alert


@pytest.mark.asyncio
async def test_list_alerts_returns_filtered_items() -> None:
    app, _, query = _build_app()
    a1 = _sample_alert(risk_score=50)  # MEDIUM
    a2 = _sample_alert(risk_score=90)  # CRITICAL
    query.add(a1)
    query.add(a2)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/alerts", params={"priority": "CRITICAL"})

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["alert_id"] == str(a2.id)
    assert body[0]["priority"] == "CRITICAL"


@pytest.mark.asyncio
async def test_list_alerts_rejects_bad_limit() -> None:
    app, _, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/alerts", params={"limit": 0})

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_alert_returns_200_when_found() -> None:
    app, _, query = _build_app()
    alert = _sample_alert()
    query.add(alert)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/api/v1/alerts/{alert.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["alert_id"] == str(alert.id)
    assert body["status"] == AlertStatus.OPEN.value
    assert body["priority"] == Priority.HIGH.value


@pytest.mark.asyncio
async def test_get_alert_returns_404_problem_details_when_missing() -> None:
    app, _, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/api/v1/alerts/{uuid4()}")

    assert resp.status_code == 404
    body = resp.json()
    assert body["title"] == "Alert not found"
    assert body["status"] == 404
    assert "trace_id" in body


@pytest.mark.asyncio
async def test_assign_happy_path() -> None:
    app, command, _ = _build_app()
    alert_id = uuid4()
    analyst = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/api/v1/alerts/{alert_id}/assign",
            json={"analyst_id": str(analyst)},
        )

    assert resp.status_code == 200
    assert resp.json()["alert_id"] == str(alert_id)
    assert command.assign_calls[0].analyst_id == analyst


@pytest.mark.asyncio
async def test_assign_rejects_unknown_field() -> None:
    app, _, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/api/v1/alerts/{uuid4()}/assign",
            json={"analyst_id": str(uuid4()), "role": "ops"},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_resolve_requires_non_empty_notes() -> None:
    app, _, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/api/v1/alerts/{uuid4()}/resolve",
            json={"resolution_notes": ""},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_resolve_maps_business_rule_violation_to_409() -> None:
    app, command, _ = _build_app()
    command.will_fail_with(
        ApplicationError.business_rule_violation("Alert", "alert must be IN_REVIEW")
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/api/v1/alerts/{uuid4()}/resolve",
            json={"resolution_notes": "confirmed"},
        )

    assert resp.status_code == 409
    body = resp.json()
    assert body["status"] == 409
    assert "alert must be IN_REVIEW" in body["detail"]


@pytest.mark.asyncio
async def test_dismiss_maps_not_found_to_404() -> None:
    app, command, _ = _build_app()
    command.will_fail_with(ApplicationError.not_found("Alert", "missing"))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/api/v1/alerts/{uuid4()}/dismiss",
            json={"reason": "false positive"},
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_health_returns_up() -> None:
    app, _, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "UP"}
