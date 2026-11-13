from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from transaction.domain.model.aggregates.transaction import Transaction
from transaction.domain.model.commands.register_transaction_command import (
    RegisterTransactionCommand,
)
from transaction.domain.model.events.transaction_registered_event import (
    TransactionRegisteredEvent,
)
from transaction.domain.model.valueobjects.account_id import AccountId
from transaction.domain.model.valueobjects.channel import Channel
from transaction.domain.model.valueobjects.money import Money


def test_register_creates_transaction_with_id_and_event(
    sample_command: RegisterTransactionCommand,
) -> None:
    tx = Transaction.register(sample_command)

    assert tx.id is not None
    events = tx.pull_events()
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, TransactionRegisteredEvent)
    assert event.transaction_id == tx.id
    assert event.account_id_hash == AccountId("acc-1").hashed()
    assert event.currency == "PEN"


def test_pull_events_clears_buffer(sample_command: RegisterTransactionCommand) -> None:
    tx = Transaction.register(sample_command)
    _ = tx.pull_events()
    assert tx.pull_events() == []


def test_restore_does_not_register_event() -> None:
    tx = Transaction.restore(
        id=__import__("uuid").uuid4(),
        account_id=AccountId("acc-1"),
        amount=Money(Decimal("10.00"), "PEN"),
        channel=Channel.WEB,
        occurred_at=datetime(2026, 11, 12, tzinfo=UTC),
    )
    assert tx.pull_events() == []


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-1")])
def test_money_rejects_non_positive(amount: Decimal) -> None:
    with pytest.raises(ValueError, match="amount must be greater than zero"):
        Money(amount=amount, currency="PEN")


def test_money_rejects_invalid_currency() -> None:
    with pytest.raises(ValueError, match="3-letter ISO code"):
        Money(amount=Decimal("1.00"), currency="PE")


def test_account_id_rejects_empty() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        AccountId("   ")


def test_account_id_hashed_is_sha256_hex() -> None:
    h = AccountId("acc-1").hashed()
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
