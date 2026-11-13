import pytest
from pydantic import ValidationError

from shared_contracts.envelope import Envelope
from shared_contracts.transactions.v1 import TransactionScoredV1


def test_roundtrip_ok(transaction_scored_raw: dict) -> None:
    env = Envelope[TransactionScoredV1].model_validate(transaction_scored_raw)

    assert env.payload.score == 87
    assert env.payload.level == "HIGH"
    assert env.payload.degraded_mode is False

    dumped = env.model_dump(mode="json")
    assert dumped["payload"]["model_version"] == "xgb-2026.11.01"


def test_tolerates_unknown_fields(transaction_scored_raw: dict) -> None:
    transaction_scored_raw["payload"]["future_metric"] = "whatever"

    env = Envelope[TransactionScoredV1].model_validate(transaction_scored_raw)

    assert env.payload.score == 87


def test_score_must_be_in_range(transaction_scored_raw: dict) -> None:
    transaction_scored_raw["payload"]["score"] = 101

    with pytest.raises(ValidationError):
        Envelope[TransactionScoredV1].model_validate(transaction_scored_raw)
