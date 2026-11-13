from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from shared_contracts.constants import TRANSACTIONS_RECEIVED_V1
from shared_contracts.envelope import Envelope
from shared_contracts.transactions.v1 import TransactionReceivedV1


def _sample_envelope_dict() -> dict:
    return {
        "message_id": str(uuid4()),
        "message_type": "TransactionReceived",
        "schema_version": 1,
        "occurred_at": datetime.now(UTC).isoformat(),
        "trace_id": "trace-abc",
        "payload": {
            "transaction_id": str(uuid4()),
            "account_id_hash": "a" * 64,
            "amount": "250.75",
            "currency": "PEN",
            "channel": "WEB",
            "device_id": "device-7421",
            "occurred_at": "2026-11-12T13:45:00Z",
        },
    }


def test_channel_constant_is_versioned() -> None:
    assert TRANSACTIONS_RECEIVED_V1 == "transactions.received.v1"


def test_envelope_roundtrip() -> None:
    raw = _sample_envelope_dict()
    env = Envelope[TransactionReceivedV1].model_validate(raw)

    assert env.payload.currency == "PEN"
    assert env.payload.amount == Decimal("250.75")
    assert env.model_dump(mode="json")["payload"]["channel"] == "WEB"


def test_envelope_tolerates_unknown_fields() -> None:
    raw = _sample_envelope_dict()
    raw["payload"]["unknown_future_field"] = "ignore me"

    env = Envelope[TransactionReceivedV1].model_validate(raw)

    assert env.payload.amount > 0


def test_payload_built_from_domain_fields_is_valid() -> None:
    payload = TransactionReceivedV1(
        transaction_id=uuid4(),
        account_id_hash="b" * 64,
        amount=Decimal("1.00"),
        currency="PEN",
        channel="MOBILE",
        device_id=None,
        occurred_at=datetime.now(UTC),
    )
    dumped = payload.model_dump(mode="json")
    assert dumped["currency"] == "PEN"
    assert dumped["device_id"] is None
