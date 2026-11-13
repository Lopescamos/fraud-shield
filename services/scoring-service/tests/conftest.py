from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)


@pytest.fixture
def sample_score_command() -> ScoreTransactionCommand:
    return ScoreTransactionCommand(
        transaction_id=uuid4(),
        account_id_hash="a" * 64,
        amount=Decimal("250.75"),
        currency="PEN",
        channel="WEB",
        occurred_at=datetime(2026, 11, 13, 13, 45, tzinfo=UTC),
        country="PE",
        device_id="device-7421",
        extra_features={"tx_count_last_5m": 1.0, "hour_of_day": 13.0},
    )
