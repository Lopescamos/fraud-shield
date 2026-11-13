from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from tests.unit.application.fakes.fake_transaction_repository import (
    FakeTransactionRepository,
)
from transaction.application.internal.commandservices.transaction_command_service_impl import (
    TransactionCommandServiceImpl,
)
from transaction.domain.model.commands.register_transaction_command import (
    RegisterTransactionCommand,
)
from transaction.domain.model.valueobjects.channel import Channel
from transaction.kernel.application.result import Failure, Success


class FakeTransaction:
    def __init__(self) -> None:
        self.is_active = True
        self.committed = False
        self.rolled_back = False

    async def rollback(self) -> None:
        self.is_active = False
        self.rolled_back = True


class FakeSession:
    def __init__(self) -> None:
        self.trans = FakeTransaction()

    @asynccontextmanager
    async def begin(self):
        yield self.trans
        self.trans.committed = True

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None


def _session_factory_with(session: FakeSession) -> Any:
    def factory() -> FakeSession:
        return session

    return factory


def _repo_builder(repo: FakeTransactionRepository) -> Any:
    def builder(_session: Any) -> FakeTransactionRepository:
        return repo

    return builder


@pytest.mark.asyncio
async def test_register_success_returns_id(
    sample_command: RegisterTransactionCommand,
) -> None:
    repo = FakeTransactionRepository()
    session = FakeSession()
    service = TransactionCommandServiceImpl(
        session_factory=_session_factory_with(session),
        repository_builder=_repo_builder(repo),
    )

    result = await service.handle(sample_command)

    assert isinstance(result, Success)
    assert await repo.find_by_id(result.value) is not None
    assert session.trans.committed is True
    assert session.trans.rolled_back is False
    assert len(repo.published_events) == 1


@pytest.mark.asyncio
async def test_register_rejects_invalid_amount(
    sample_command: RegisterTransactionCommand,
) -> None:
    invalid = RegisterTransactionCommand(
        account_id="acc-1",
        amount=Decimal("0"),
        currency="PEN",
        channel=Channel.WEB,
        occurred_at=sample_command.occurred_at,
    )
    repo = FakeTransactionRepository()
    session = FakeSession()
    service = TransactionCommandServiceImpl(
        session_factory=_session_factory_with(session),
        repository_builder=_repo_builder(repo),
    )

    result = await service.handle(invalid)

    assert isinstance(result, Failure)
    assert result.error.code == "validation_error"
    assert session.trans.rolled_back is True


@pytest.mark.asyncio
async def test_register_with_idempotency_key_returns_same_id(
    sample_command: RegisterTransactionCommand,
) -> None:
    repo = FakeTransactionRepository()

    first_session = FakeSession()
    service1 = TransactionCommandServiceImpl(
        session_factory=_session_factory_with(first_session),
        repository_builder=_repo_builder(repo),
    )
    first = await service1.handle(sample_command, idempotency_key="abc-123")
    assert isinstance(first, Success)

    second_session = FakeSession()
    service2 = TransactionCommandServiceImpl(
        session_factory=_session_factory_with(second_session),
        repository_builder=_repo_builder(repo),
    )
    second = await service2.handle(sample_command, idempotency_key="abc-123")
    assert isinstance(second, Success)
    assert second.value == first.value
    assert len(repo.published_events) == 1


@pytest.mark.asyncio
async def test_register_repository_failure_rolls_back(
    sample_command: RegisterTransactionCommand,
) -> None:
    class FailingRepo(FakeTransactionRepository):
        async def save(self, transaction):  # type: ignore[override]
            raise RuntimeError("boom")

    session = FakeSession()
    service = TransactionCommandServiceImpl(
        session_factory=_session_factory_with(session),
        repository_builder=_repo_builder(FailingRepo()),
    )

    result = await service.handle(sample_command)

    assert isinstance(result, Failure)
    assert result.error.code == "unexpected"
    assert session.trans.rolled_back is True


# make SimpleNamespace unused import visible to linters: not needed.
_ = SimpleNamespace
