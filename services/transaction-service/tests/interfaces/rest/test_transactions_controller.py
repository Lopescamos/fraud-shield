from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from transaction.domain.model.aggregates.transaction import Transaction
from transaction.domain.model.commands.register_transaction_command import (
    RegisterTransactionCommand,
)
from transaction.domain.model.valueobjects.account_id import AccountId
from transaction.domain.model.valueobjects.channel import Channel
from transaction.domain.model.valueobjects.money import Money
from transaction.interfaces.rest import exception_handlers
from transaction.interfaces.rest.health_controller import router as health_router
from transaction.interfaces.rest.transactions_controller import router as tx_router
from transaction.kernel.application.result import (
    ApplicationError,
    Failure,
    Success,
)


class FakeCommandService:
    def __init__(self) -> None:
        self.calls: list[tuple[RegisterTransactionCommand, str | None]] = []
        self._next_id: UUID | None = None
        self._next_failure: ApplicationError | None = None
        self._by_key: dict[str, UUID] = {}

    def will_return(self, transaction_id: UUID) -> None:
        self._next_id = transaction_id
        self._next_failure = None

    def will_fail_with(self, error: ApplicationError) -> None:
        self._next_failure = error
        self._next_id = None

    async def handle(
        self,
        command: RegisterTransactionCommand,
        idempotency_key: str | None = None,
    ):
        self.calls.append((command, idempotency_key))
        if self._next_failure is not None:
            return Failure(self._next_failure)
        if idempotency_key is not None and idempotency_key in self._by_key:
            return Success(self._by_key[idempotency_key])
        new_id = self._next_id or uuid4()
        if idempotency_key is not None:
            self._by_key[idempotency_key] = new_id
        return Success(new_id)


class FakeQueryService:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Transaction] = {}

    def add(self, tx: Transaction) -> None:
        self._by_id[tx.id] = tx

    async def handle(self, query):
        return self._by_id.get(query.transaction_id)


def _build_app() -> tuple[FastAPI, FakeCommandService, FakeQueryService]:
    command = FakeCommandService()
    query = FakeQueryService()
    app = FastAPI()
    app.state.transaction_command_service = command
    app.state.transaction_query_service = query
    exception_handlers.register(app)
    app.include_router(health_router)
    app.include_router(tx_router)
    return app, command, query


def _valid_body() -> dict:
    return {
        "account_id": "acc-1",
        "amount": "100.00",
        "currency": "PEN",
        "channel": "WEB",
        "occurred_at": datetime.now(UTC).isoformat(),
        "device_id": "device-1",
    }


@pytest.mark.asyncio
async def test_post_returns_202_with_transaction_id() -> None:
    app, command, _ = _build_app()
    tx_id = uuid4()
    command.will_return(tx_id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/transactions", json=_valid_body())

    assert resp.status_code == 202
    assert resp.json()["transaction_id"] == str(tx_id)
    assert command.calls[0][1] is None


@pytest.mark.asyncio
async def test_post_rejects_invalid_amount() -> None:
    app, _, _ = _build_app()
    body = _valid_body()
    body["amount"] = "0"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/transactions", json=body)

    assert resp.status_code == 422
    payload = resp.json()
    assert payload["title"] == "Validation failed"
    assert payload["status"] == 422
    assert payload["errors"]


@pytest.mark.asyncio
async def test_post_rejects_unknown_field() -> None:
    app, _, _ = _build_app()
    body = _valid_body()
    body["unexpected"] = "yes"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/transactions", json=body)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_idempotency_key_returns_same_transaction_id() -> None:
    app, command, _ = _build_app()
    tx_id = uuid4()
    command.will_return(tx_id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = await client.post(
            "/api/v1/transactions",
            json=_valid_body(),
            headers={"Idempotency-Key": "abc"},
        )
        second = await client.post(
            "/api/v1/transactions",
            json=_valid_body(),
            headers={"Idempotency-Key": "abc"},
        )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["transaction_id"] == second.json()["transaction_id"]
    assert command.calls[0][1] == "abc"
    assert command.calls[1][1] == "abc"


@pytest.mark.asyncio
async def test_get_returns_200_when_found() -> None:
    app, _, query = _build_app()
    tx = Transaction.restore(
        id=uuid4(),
        account_id=AccountId("acc-1"),
        amount=Money(Decimal("10.00"), "PEN"),
        channel=Channel.WEB,
        occurred_at=datetime.now(UTC),
        device_id="device-1",
    )
    query.add(tx)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/api/v1/transactions/{tx.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["transaction_id"] == str(tx.id)
    assert body["currency"] == "PEN"


@pytest.mark.asyncio
async def test_get_returns_404_when_missing() -> None:
    app, _, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/api/v1/transactions/{uuid4()}")

    assert resp.status_code == 404
    body = resp.json()
    assert body["title"] == "Transaction not found"
    assert body["status"] == 404


@pytest.mark.asyncio
async def test_health_returns_up() -> None:
    app, _, _ = _build_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "UP"}
