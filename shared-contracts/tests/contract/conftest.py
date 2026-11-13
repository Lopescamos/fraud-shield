"""Fixtures with a valid raw envelope per V1 contract."""
from __future__ import annotations

import pytest

ACCOUNT_HASH = "a" * 64


@pytest.fixture
def transaction_received_raw() -> dict:
    return {
        "message_id": "0f3f8b7e-6b6a-4f1e-9d6a-1b1e2c3d4e5f",
        "message_type": "TransactionReceived",
        "schema_version": 1,
        "occurred_at": "2026-11-12T13:45:00Z",
        "trace_id": "01HSZK2A7F5V4N1Q4X2TB3W7PH",
        "payload": {
            "transaction_id": "9b6c3f12-1111-2222-3333-444455556666",
            "account_id_hash": ACCOUNT_HASH,
            "amount": "480.00",
            "currency": "PEN",
            "channel": "WEB",
            "device_id": "device-7421",
            "occurred_at": "2026-11-12T13:45:00Z",
        },
    }


@pytest.fixture
def transaction_scored_raw() -> dict:
    return {
        "message_id": "1a1a1a1a-2b2b-3c3c-4d4d-5e5e5e5e5e5e",
        "message_type": "TransactionScored",
        "schema_version": 1,
        "occurred_at": "2026-11-12T13:45:02Z",
        "trace_id": "01HSZK2A7F5V4N1Q4X2TB3W7PH",
        "payload": {
            "assessment_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "transaction_id": "9b6c3f12-1111-2222-3333-444455556666",
            "account_id_hash": ACCOUNT_HASH,
            "score": 87,
            "level": "HIGH",
            "rules_score": 40,
            "xgb_probability": "0.912",
            "iforest_anomaly": "0.734",
            "degraded_mode": False,
            "model_version": "xgb-2026.11.01",
            "occurred_at": "2026-11-12T13:45:02Z",
        },
    }


@pytest.fixture
def alert_raised_raw() -> dict:
    return {
        "message_id": "2b2b2b2b-3c3c-4d4d-5e5e-6f6f6f6f6f6f",
        "message_type": "AlertRaised",
        "schema_version": 1,
        "occurred_at": "2026-11-12T13:45:03Z",
        "trace_id": "01HSZK2A7F5V4N1Q4X2TB3W7PH",
        "payload": {
            "alert_id": "cccccccc-dddd-eeee-ffff-000011112222",
            "transaction_id": "9b6c3f12-1111-2222-3333-444455556666",
            "account_id_hash": ACCOUNT_HASH,
            "severity": "HIGH",
            "score": 87,
            "level": "HIGH",
            "opened_at": "2026-11-12T13:45:03Z",
        },
    }


@pytest.fixture
def alert_resolved_raw() -> dict:
    return {
        "message_id": "3c3c3c3c-4d4d-5e5e-6f6f-707070707070",
        "message_type": "AlertResolved",
        "schema_version": 1,
        "occurred_at": "2026-11-12T14:10:00Z",
        "trace_id": "01HSZK2A7F5V4N1Q4X2TB3W7PH",
        "payload": {
            "alert_id": "cccccccc-dddd-eeee-ffff-000011112222",
            "transaction_id": "9b6c3f12-1111-2222-3333-444455556666",
            "previous_status": "IN_REVIEW",
            "new_status": "CONFIRMED",
            "analyst_id": "11111111-2222-3333-4444-555555555555",
            "reason": "confirmed by fraud squad",
            "closed_at": "2026-11-12T14:10:00Z",
        },
    }
