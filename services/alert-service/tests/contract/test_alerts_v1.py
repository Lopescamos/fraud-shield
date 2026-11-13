from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from shared_contracts.alerts.v1 import AlertRaisedV1, AlertResolvedV1
from shared_contracts.constants import ALERTS_RAISED_V1, ALERTS_RESOLVED_V1
from shared_contracts.envelope import Envelope


def _raised_dict() -> dict:
    return {
        "message_id": str(uuid4()),
        "message_type": "AlertRaised",
        "schema_version": 1,
        "occurred_at": datetime.now(UTC).isoformat(),
        "trace_id": "trace-abc",
        "payload": {
            "alert_id": str(uuid4()),
            "transaction_id": str(uuid4()),
            "account_id_hash": "a" * 64,
            "severity": "HIGH",
            "score": 82,
            "level": "HIGH",
            "opened_at": "2026-11-13T10:00:00Z",
        },
    }


def _resolved_dict() -> dict:
    return {
        "message_id": str(uuid4()),
        "message_type": "AlertResolved",
        "schema_version": 1,
        "occurred_at": datetime.now(UTC).isoformat(),
        "trace_id": "trace-def",
        "payload": {
            "alert_id": str(uuid4()),
            "transaction_id": str(uuid4()),
            "previous_status": "IN_REVIEW",
            "new_status": "RESOLVED",
            "analyst_id": str(uuid4()),
            "reason": "confirmed fraud",
            "closed_at": "2026-11-13T11:00:00Z",
        },
    }


def test_channel_constants_are_versioned() -> None:
    assert ALERTS_RAISED_V1 == "alerts.raised.v1"
    assert ALERTS_RESOLVED_V1 == "alerts.resolved.v1"


def test_alert_raised_envelope_roundtrip() -> None:
    env = Envelope[AlertRaisedV1].model_validate(_raised_dict())
    assert env.payload.severity == "HIGH"
    assert env.payload.score == 82


def test_alert_raised_tolerates_unknown_fields() -> None:
    raw = _raised_dict()
    raw["payload"]["new_future_field"] = "ignore"
    env = Envelope[AlertRaisedV1].model_validate(raw)
    assert env.payload.score == 82


def test_alert_resolved_envelope_roundtrip() -> None:
    env = Envelope[AlertResolvedV1].model_validate(_resolved_dict())
    assert env.payload.previous_status == "IN_REVIEW"
    assert env.payload.new_status == "RESOLVED"
    assert env.payload.reason == "confirmed fraud"


def test_alert_resolved_accepts_dismissed() -> None:
    raw = _resolved_dict()
    raw["payload"]["new_status"] = "DISMISSED"
    raw["payload"]["reason"] = "false positive"
    env = Envelope[AlertResolvedV1].model_validate(raw)
    assert env.payload.new_status == "DISMISSED"
