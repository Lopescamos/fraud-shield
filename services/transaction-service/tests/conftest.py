from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from transaction.domain.model.commands.register_transaction_command import (
    RegisterTransactionCommand,
)
from transaction.domain.model.valueobjects.channel import Channel


@pytest.fixture
def sample_command() -> RegisterTransactionCommand:
    return RegisterTransactionCommand(
        account_id="acc-1",
        amount=Decimal("100.00"),
        currency="PEN",
        channel=Channel.WEB,
        occurred_at=datetime(2026, 11, 12, 13, 45, tzinfo=UTC),
        device_id="device-7421",
    )
