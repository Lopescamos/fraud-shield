from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from analytics.application.dto.read_dtos import (
    AlertDTO,
    DailyMetricDTO,
    SummaryMetricDTO,
    TransactionDTO,
)
from analytics.interfaces.rest import exception_handlers
from analytics.interfaces.rest.analytics_controller import router as analytics_router
from analytics.interfaces.rest.health_controller import router as health_router
from analytics.interfaces.rest.security import api_key

VALID_KEY = "test-key"


class FakeQueryService:
    def __init__(self) -> None:
        self._transactions: list[TransactionDTO] = []
        self._alerts: list[AlertDTO] = []
        self._daily: list[DailyMetricDTO] = []
        self._summary = SummaryMetricDTO(
            total_transactions=0,
            total_alerts=0,
            open_alerts=0,
            in_review_alerts=0,
            resolved_alerts=0,
            dismissed_alerts=0,
            blocked_transactions=0,
            review_transactions=0,
            fraud_rate=0.0,
        )
        self.last_filters: dict = {}

    def seed_transactions(self, dtos: list[TransactionDTO]) -> None:
        self._transactions = dtos

    def seed_alerts(self, dtos: list[AlertDTO]) -> None:
        self._alerts = dtos

    def seed_daily(self, dtos: list[DailyMetricDTO]) -> None:
        self._daily = dtos

    def seed_summary(self, dto: SummaryMetricDTO) -> None:
        self._summary = dto

    async def list_transactions(self, query):
        self.last_filters = {"transactions": query}
        return list(self._transactions)

    async def list_alerts(self, query):
        self.last_filters = {"alerts": query}
        return list(self._alerts)

    async def daily_metrics(self, query):
        self.last_filters = {"daily": query}
        return list(self._daily)

    async def summary_metrics(self, query):
        self.last_filters = {"summary": query}
        return self._summary


def _build_app() -> tuple[FastAPI, FakeQueryService]:
    app = FastAPI()
    service = FakeQueryService()
    app.state.query_application_service = service
    api_key.register(app, {VALID_KEY})
    exception_handlers.register(app)
    app.include_router(health_router)
    app.include_router(analytics_router)
    return app, service


def _tx_dto() -> TransactionDTO:
    return TransactionDTO(
        transaction_id=uuid4(),
        account_id_hash="a" * 64,
        amount=Decimal("250.00"),
        currency="PEN",
        channel="WEB",
        country="PE",
        device_id="d-1",
        occurred_at=datetime(2026, 11, 14, 13, tzinfo=UTC),
        received_at=datetime(2026, 11, 14, 13, tzinfo=UTC),
        risk_score=82,
        level="HIGH",
        decision="REVIEW",
        model_version="xgb-v1",
        degraded_mode=False,
        scored_at=datetime(2026, 11, 14, 13, 1, tzinfo=UTC),
    )


def _alert_dto() -> AlertDTO:
    return AlertDTO(
        alert_id=uuid4(),
        transaction_id=uuid4(),
        account_id_hash="b" * 64,
        priority="CRITICAL",
        score=95,
        level="CRITICAL",
        status="OPEN",
        opened_at=datetime(2026, 11, 14, tzinfo=UTC),
        analyst_id=None,
        resolution=None,
        closed_at=None,
    )


@pytest.mark.asyncio
async def test_missing_api_key_returns_401_problem_details() -> None:
    app, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/analytics/transactions")

    assert resp.status_code == 401
    body = resp.json()
    assert body["status"] == 401
    assert body["title"] == "Missing or invalid API key"
    assert "trace_id" in body


@pytest.mark.asyncio
async def test_invalid_api_key_returns_401() -> None:
    app, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/analytics/transactions", headers={"X-API-Key": "wrong"}
        )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_is_reachable_without_api_key() -> None:
    app, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "UP"}


@pytest.mark.asyncio
async def test_list_transactions_returns_dtos() -> None:
    app, service = _build_app()
    dto = _tx_dto()
    service.seed_transactions([dto])

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/analytics/transactions", headers={"X-API-Key": VALID_KEY}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["transaction_id"] == str(dto.transaction_id)
    assert body[0]["decision"] == "REVIEW"


@pytest.mark.asyncio
async def test_list_transactions_forwards_filters() -> None:
    app, service = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/analytics/transactions",
            headers={"X-API-Key": VALID_KEY},
            params={
                "decision": "BLOCK",
                "country": "PE",
                "limit": 50,
                "offset": 10,
            },
        )

    assert resp.status_code == 200
    q = service.last_filters["transactions"]
    assert q.decision.value == "BLOCK"
    assert q.country == "PE"
    assert q.limit == 50
    assert q.offset == 10


@pytest.mark.asyncio
async def test_list_transactions_rejects_limit_zero() -> None:
    app, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/analytics/transactions",
            headers={"X-API-Key": VALID_KEY},
            params={"limit": 0},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_alerts_returns_dtos() -> None:
    app, service = _build_app()
    service.seed_alerts([_alert_dto()])

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/analytics/alerts",
            headers={"X-API-Key": VALID_KEY},
            params={"priority": "CRITICAL"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["priority"] == "CRITICAL"


@pytest.mark.asyncio
async def test_daily_metrics_requires_date_range() -> None:
    app, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/analytics/metrics/daily", headers={"X-API-Key": VALID_KEY}
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_daily_metrics_rejects_inverted_range() -> None:
    app, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/analytics/metrics/daily",
            headers={"X-API-Key": VALID_KEY},
            params={
                "date_from": "2026-11-14T00:00:00Z",
                "date_to": "2026-11-13T00:00:00Z",
            },
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_summary_metrics_returns_flat_dto() -> None:
    app, service = _build_app()
    service.seed_summary(
        SummaryMetricDTO(
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
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/analytics/metrics/summary", headers={"X-API-Key": VALID_KEY}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_transactions"] == 1_000
    assert body["fraud_rate"] == 0.05
