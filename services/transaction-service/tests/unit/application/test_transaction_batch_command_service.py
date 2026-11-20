from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tests.unit.application.fakes.fake_transaction_repository import (
    FakeTransactionRepository,
)
from tests.unit.application.test_transaction_command_service import FakeSession
from transaction.application.internal.commandservices.transaction_batch_command_service_impl import (
    TransactionBatchCommandServiceImpl,
)
from transaction.domain.model.commands.register_batch_transactions_command import (
    RegisterBatchTransactionsCommand,
)
from transaction.domain.model.commands.register_transaction_command import (
    RegisterTransactionCommand,
)
from transaction.domain.model.valueobjects.channel import Channel


def _item(account: str = "acc-1", amount: str = "10.00") -> RegisterTransactionCommand:
    return RegisterTransactionCommand(
        account_id=account,
        amount=Decimal(amount),
        currency="PEN",
        channel=Channel.WEB,
        occurred_at=datetime(2026, 11, 19, tzinfo=UTC),
    )


def _service(repo: FakeTransactionRepository, session: FakeSession):
    return TransactionBatchCommandServiceImpl(
        session_factory=lambda: session,
        repository_builder=lambda _s: repo,
    )


@pytest.mark.asyncio
async def test_empty_batch_returns_empty_outcomes() -> None:
    svc = _service(FakeTransactionRepository(), FakeSession())
    outcomes = await svc.handle(RegisterBatchTransactionsCommand(items=[]))
    assert outcomes == []


@pytest.mark.asyncio
async def test_happy_path_registers_every_item() -> None:
    repo = FakeTransactionRepository()
    svc = _service(repo, FakeSession())
    cmd = RegisterBatchTransactionsCommand(items=[_item(), _item(account="acc-2")])

    outcomes = await svc.handle(cmd)

    assert len(outcomes) == 2
    assert all(o.ok for o in outcomes)
    assert all(o.transaction_id is not None for o in outcomes)
    assert len(repo.published_events) == 2


@pytest.mark.asyncio
async def test_invalid_item_is_rejected_without_failing_the_batch() -> None:
    repo = FakeTransactionRepository()
    svc = _service(repo, FakeSession())
    cmd = RegisterBatchTransactionsCommand(
        items=[_item(), _item(amount="0"), _item(account="acc-3")]
    )

    outcomes = await svc.handle(cmd)

    assert len(outcomes) == 3
    assert outcomes[0].ok
    assert not outcomes[1].ok
    assert outcomes[1].error is not None
    assert outcomes[1].error.code == "validation_error"
    assert outcomes[2].ok


@pytest.mark.asyncio
async def test_batch_rejects_over_max_size() -> None:
    svc = _service(FakeTransactionRepository(), FakeSession())
    cmd = RegisterBatchTransactionsCommand(
        items=[_item() for _ in range(RegisterBatchTransactionsCommand.MAX_SIZE + 1)]
    )

    outcomes = await svc.handle(cmd)

    assert len(outcomes) == 1
    assert not outcomes[0].ok
    assert outcomes[0].error is not None
    assert "max size" in outcomes[0].error.detail


@pytest.mark.asyncio
async def test_idempotency_header_derives_per_item_keys() -> None:
    repo = FakeTransactionRepository()
    svc = _service(repo, FakeSession())
    cmd = RegisterBatchTransactionsCommand(items=[_item(), _item(account="acc-2")])

    first = await svc.handle(cmd, idempotency_key="batch-1")
    assert all(o.ok for o in first)
    first_ids = [o.transaction_id for o in first]

    # Replay the same batch with the same key: no new rows, same ids.
    svc2 = _service(repo, FakeSession())
    second = await svc2.handle(cmd, idempotency_key="batch-1")

    second_ids = [o.transaction_id for o in second]
    assert second_ids == first_ids
    assert len(repo.published_events) == 2  # still 2, not 4
