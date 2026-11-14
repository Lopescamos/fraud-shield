from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from shared_contracts.alerts.v1 import AlertRaisedV1, AlertResolvedV1
from shared_contracts.envelope import Envelope
from shared_contracts.transactions.v1 import TransactionReceivedV1, TransactionScoredV1


def _wrap(payload: dict, message_type: str) -> dict:
    return {
        "message_id": str(uuid4()),
        "message_type": message_type,
        "schema_version": 1,
        "occurred_at": datetime.now(UTC).isoformat(),
        "trace_id": "trace-xyz",
        "payload": payload,
    }


def test_envelope_transaction_received_roundtrip_tolerates_unknown() -> None:
    raw = _wrap(
        {
            "transaction_id": str(uuid4()),
            "account_id_hash": "a" * 64,
            "amount": "250.75",
            "currency": "PEN",
            "channel": "WEB",
            "device_id": "d-1",
            "occurred_at": "2026-11-14T13:45:00Z",
            "new_future_field": "ignored",
        },
        "TransactionReceived",
    )
    env = Envelope[TransactionReceivedV1].model_validate(raw)
    assert env.payload.amount == Decimal("250.75")


def test_envelope_transaction_scored_roundtrip_tolerates_unknown() -> None:
    raw = _wrap(
        {
            "assessment_id": str(uuid4()),
            "transaction_id": str(uuid4()),
            "account_id_hash": "b" * 64,
            "score": 82,
            "level": "HIGH",
            "rules_score": 60,
            "xgb_probability": "0.70",
            "iforest_anomaly": "0.20",
            "degraded_mode": False,
            "model_version": "xgb-v1",
            "occurred_at": "2026-11-14T13:45:00Z",
            "future_metric": "ignored",
        },
        "TransactionScored",
    )
    env = Envelope[TransactionScoredV1].model_validate(raw)
    assert env.payload.score == 82


def test_envelope_alert_raised_roundtrip() -> None:
    raw = _wrap(
        {
            "alert_id": str(uuid4()),
            "transaction_id": str(uuid4()),
            "account_id_hash": "c" * 64,
            "severity": "HIGH",
            "score": 82,
            "level": "HIGH",
            "opened_at": "2026-11-14T13:45:00Z",
        },
        "AlertRaised",
    )
    env = Envelope[AlertRaisedV1].model_validate(raw)
    assert env.payload.severity == "HIGH"


def test_envelope_alert_resolved_roundtrip() -> None:
    raw = _wrap(
        {
            "alert_id": str(uuid4()),
            "transaction_id": str(uuid4()),
            "previous_status": "IN_REVIEW",
            "new_status": "RESOLVED",
            "analyst_id": str(uuid4()),
            "reason": "confirmed",
            "closed_at": "2026-11-14T14:00:00Z",
        },
        "AlertResolved",
    )
    env = Envelope[AlertResolvedV1].model_validate(raw)
    assert env.payload.new_status == "RESOLVED"
