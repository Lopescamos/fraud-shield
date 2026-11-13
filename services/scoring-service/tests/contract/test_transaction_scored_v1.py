from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from shared_contracts.constants import TRANSACTIONS_SCORED_V1
from shared_contracts.envelope import Envelope
from shared_contracts.transactions.v1 import TransactionScoredV1


def _sample_envelope_dict() -> dict:
    return {
        "message_id": str(uuid4()),
        "message_type": "TransactionScored",
        "schema_version": 1,
        "occurred_at": datetime.now(UTC).isoformat(),
        "trace_id": "trace-def",
        "payload": {
            "assessment_id": str(uuid4()),
            "transaction_id": str(uuid4()),
            "account_id_hash": "b" * 64,
            "score": 62,
            "level": "MEDIUM",
            "rules_score": 40,
            "xgb_probability": "0.70",
            "iforest_anomaly": "0.20",
            "degraded_mode": False,
            "model_version": "xgb-prod-1",
            "occurred_at": "2026-11-13T13:45:00Z",
        },
    }


def test_channel_constant_is_versioned() -> None:
    assert TRANSACTIONS_SCORED_V1 == "transactions.scored.v1"


def test_envelope_roundtrip() -> None:
    raw = _sample_envelope_dict()
    env = Envelope[TransactionScoredV1].model_validate(raw)

    assert env.payload.score == 62
    assert env.payload.level == "MEDIUM"
    dumped = env.model_dump(mode="json")["payload"]
    assert dumped["model_version"] == "xgb-prod-1"


def test_envelope_tolerates_unknown_fields() -> None:
    raw = _sample_envelope_dict()
    raw["payload"]["new_future_field"] = "ignore"

    env = Envelope[TransactionScoredV1].model_validate(raw)

    assert env.payload.score == 62


def test_payload_built_from_domain_fields_is_valid() -> None:
    payload = TransactionScoredV1(
        assessment_id=uuid4(),
        transaction_id=uuid4(),
        account_id_hash="c" * 64,
        score=90,
        level="CRITICAL",
        rules_score=60,
        xgb_probability=Decimal("0.95"),
        iforest_anomaly=Decimal("0.80"),
        degraded_mode=False,
        model_version="xgb-prod-7",
        occurred_at=datetime.now(UTC),
    )
    dumped = payload.model_dump(mode="json")
    assert dumped["level"] == "CRITICAL"
    assert dumped["degraded_mode"] is False
