from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from scoring.domain.model.aggregates.scoring_result import ScoringResult
from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.domain.model.valueobjects.decision import Decision
from scoring.domain.model.valueobjects.model_version import ModelVersion
from scoring.domain.model.valueobjects.risk_factor import RiskFactor
from scoring.domain.model.valueobjects.risk_score import RiskScore
from scoring.interfaces.rest import exception_handlers
from scoring.interfaces.rest.health_controller import router as health_router
from scoring.interfaces.rest.scores_controller import router as scores_router
from scoring.kernel.application.result import (
    ApplicationError,
    Failure,
    Success,
)


class FakeCommandService:
    def __init__(self) -> None:
        self.calls: list[tuple[ScoreTransactionCommand, str | None]] = []
        self._next_id: UUID | None = None
        self._next_failure: ApplicationError | None = None
        self._by_tx: dict[UUID, UUID] = {}

    def will_return(self, scoring_result_id: UUID) -> None:
        self._next_id = scoring_result_id
        self._next_failure = None

    def will_fail_with(self, error: ApplicationError) -> None:
        self._next_failure = error
        self._next_id = None

    async def handle(self, command, idempotency_key=None):
        self.calls.append((command, idempotency_key))
        if self._next_failure is not None:
            return Failure(self._next_failure)
        tx_id = command.transaction_id
        if tx_id in self._by_tx:
            return Success(self._by_tx[tx_id])
        new_id = self._next_id or uuid4()
        self._by_tx[tx_id] = new_id
        return Success(new_id)


class FakeQueryService:
    def __init__(self) -> None:
        self._by_id: dict[UUID, ScoringResult] = {}

    def add(self, result: ScoringResult) -> None:
        self._by_id[result.id] = result

    async def handle(self, query):
        return self._by_id.get(query.scoring_result_id)


def _build_app() -> tuple[FastAPI, FakeCommandService, FakeQueryService]:
    command = FakeCommandService()
    query = FakeQueryService()
    app = FastAPI()
    app.state.scoring_application_service = command
    app.state.scoring_result_query_service = query
    exception_handlers.register(app)
    app.include_router(health_router)
    app.include_router(scores_router)
    return app, command, query


def _valid_body() -> dict:
    return {
        "transaction_id": str(uuid4()),
        "account_id_hash": "a" * 64,
        "amount": "250.75",
        "currency": "PEN",
        "channel": "WEB",
        "occurred_at": datetime.now(UTC).isoformat(),
        "country": "PE",
        "device_id": "device-1",
        "extra_features": {"tx_count_last_5m": 2.0},
    }


def _sample_result() -> ScoringResult:
    return ScoringResult.restore(
        id=uuid4(),
        transaction_id=uuid4(),
        account_id_hash="b" * 64,
        score=RiskScore(55.0),
        decision=Decision.REVIEW,
        level="MEDIUM",
        rules_score=40,
        xgb_probability=Decimal("0.7"),
        iforest_anomaly=Decimal("0.2"),
        model_version=ModelVersion("xgb-v2"),
        degraded_mode=False,
        factors=[
            RiskFactor(feature="amount_log", weight=0.3, direction="increase")
        ],
        occurred_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_post_returns_202_with_scoring_result_id() -> None:
    app, command, _ = _build_app()
    scoring_id = uuid4()
    command.will_return(scoring_id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/scores", json=_valid_body())

    assert resp.status_code == 202
    assert resp.json()["scoring_result_id"] == str(scoring_id)


@pytest.mark.asyncio
async def test_post_rejects_unknown_field() -> None:
    app, _, _ = _build_app()
    body = _valid_body()
    body["forbidden"] = "yes"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/scores", json=body)

    assert resp.status_code == 422
    payload = resp.json()
    assert payload["title"] == "Validation failed"


@pytest.mark.asyncio
async def test_post_rejects_invalid_amount() -> None:
    app, _, _ = _build_app()
    body = _valid_body()
    body["amount"] = "0"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/scores", json=body)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_passes_idempotency_key_header() -> None:
    app, command, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/scores",
            json=_valid_body(),
            headers={"Idempotency-Key": "abc-123"},
        )

    assert resp.status_code == 202
    assert command.calls[0][1] == "abc-123"


@pytest.mark.asyncio
async def test_get_returns_200_when_found() -> None:
    app, _, query = _build_app()
    result = _sample_result()
    query.add(result)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/api/v1/scores/{result.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["scoring_result_id"] == str(result.id)
    assert body["level"] == "MEDIUM"
    assert body["decision"] == "REVIEW"
    assert body["model_version"] == "xgb-v2"
    assert len(body["factors"]) == 1


@pytest.mark.asyncio
async def test_get_returns_404_problem_details_when_missing() -> None:
    app, _, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/api/v1/scores/{uuid4()}")

    assert resp.status_code == 404
    body = resp.json()
    assert body["title"] == "Scoring result not found"
    assert body["status"] == 404
    assert "trace_id" in body


@pytest.mark.asyncio
async def test_health_returns_up() -> None:
    app, _, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "UP"}
