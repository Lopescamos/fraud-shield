from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from transaction.application.internal.eventhandlers.transaction_registered_event_handler import (
    TransactionRegisteredEventHandler,
)
from transaction.domain.model.aggregates.transaction import Transaction
from transaction.domain.model.commands.register_transaction_command import (
    RegisterTransactionCommand,
)
from transaction.domain.model.events.transaction_registered_event import (
    TransactionRegisteredEvent,
)
from transaction.domain.model.valueobjects.channel import Channel
from transaction.infrastructure.messaging.outbox.outbox_message_publisher import (
    OutboxMessagePublisher,
)
from transaction.infrastructure.messaging.outbox.outbox_persistence_entity import (
    OutboxPersistenceEntity,
)
from transaction.infrastructure.persistence.repositories.transaction_repository_impl import (
    TransactionRepositoryImpl,
)
from transaction.kernel.domain.event_dispatcher import EventDispatcher

pytestmark = pytest.mark.integration


def _build_repo(session) -> TransactionRepositoryImpl:
    publisher = OutboxMessagePublisher(session)
    handler = TransactionRegisteredEventHandler(publisher)
    dispatcher = EventDispatcher()
    dispatcher.register(TransactionRegisteredEvent, handler.on_transaction_registered)
    return TransactionRepositoryImpl(session, dispatcher)


@pytest.mark.asyncio
async def test_save_and_find(session) -> None:
    async with session.begin():
        repo = _build_repo(session)
        command = RegisterTransactionCommand(
            account_id="acc-persist",
            amount=Decimal("200.00"),
            currency="PEN",
            channel=Channel.WEB,
            occurred_at=datetime(2026, 11, 12, 13, 45, tzinfo=UTC),
            device_id="device-1",
        )
        saved = await repo.save(Transaction.register(command))

    async with session.begin():
        found = await repo.find_by_id(saved.id)

    assert found is not None
    assert found.amount.amount == Decimal("200.00")
    assert found.channel == Channel.WEB
    assert found.device_id == "device-1"


@pytest.mark.asyncio
async def test_save_writes_outbox_row(session) -> None:
    async with session.begin():
        repo = _build_repo(session)
        command = RegisterTransactionCommand(
            account_id="acc-outbox",
            amount=Decimal("55.00"),
            currency="PEN",
            channel=Channel.MOBILE,
            occurred_at=datetime(2026, 11, 12, 14, 0, tzinfo=UTC),
        )
        await repo.save(Transaction.register(command))

    rows = (
        await session.execute(
            select(OutboxPersistenceEntity).where(
                OutboxPersistenceEntity.channel == "transactions.received.v1"
            )
        )
    ).scalars().all()
    assert len(rows) >= 1
    row = rows[-1]
    assert row.message_type == "TransactionReceived"
    assert row.status == "PENDING"
    assert row.payload["payload"]["currency"] == "PEN"


@pytest.mark.asyncio
async def test_idempotency_key_roundtrip(session) -> None:
    async with session.begin():
        repo = _build_repo(session)
        command = RegisterTransactionCommand(
            account_id="acc-idem",
            amount=Decimal("1.00"),
            currency="PEN",
            channel=Channel.POS,
            occurred_at=datetime(2026, 11, 12, 15, 0, tzinfo=UTC),
        )
        tx = await repo.save(Transaction.register(command))
        await repo.save_idempotency_key("header-123", tx.id)

    async with session.begin():
        found = await repo.find_by_idempotency_key("header-123")

    assert found == tx.id
