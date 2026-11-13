from decimal import Decimal

from shared_contracts.envelope import Envelope
from shared_contracts.transactions.v1 import TransactionReceivedV1


def test_roundtrip_ok(transaction_received_raw: dict) -> None:
    env = Envelope[TransactionReceivedV1].model_validate(transaction_received_raw)

    assert env.payload.transaction_id.hex == "9b6c3f12111122223333444455556666"
    assert env.payload.currency == "PEN"
    assert env.payload.amount == Decimal("480.00")

    dumped = env.model_dump(mode="json")
    assert dumped["payload"]["currency"] == "PEN"
    assert dumped["payload"]["channel"] == "WEB"


def test_tolerates_unknown_fields(transaction_received_raw: dict) -> None:
    transaction_received_raw["payload"]["unknown_future_field"] = "ignore me"
    transaction_received_raw["unknown_envelope_field"] = 42

    env = Envelope[TransactionReceivedV1].model_validate(transaction_received_raw)

    assert env.payload.amount > 0
    assert not hasattr(env.payload, "unknown_future_field")


def test_device_id_is_optional(transaction_received_raw: dict) -> None:
    transaction_received_raw["payload"].pop("device_id")

    env = Envelope[TransactionReceivedV1].model_validate(transaction_received_raw)

    assert env.payload.device_id is None
