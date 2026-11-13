from shared_contracts.alerts.v1 import AlertResolvedV1
from shared_contracts.envelope import Envelope


def test_roundtrip_ok(alert_resolved_raw: dict) -> None:
    env = Envelope[AlertResolvedV1].model_validate(alert_resolved_raw)

    assert env.payload.previous_status == "IN_REVIEW"
    assert env.payload.new_status == "CONFIRMED"
    assert env.payload.reason == "confirmed by fraud squad"


def test_tolerates_unknown_fields(alert_resolved_raw: dict) -> None:
    alert_resolved_raw["payload"]["closed_channel"] = "WEB"

    env = Envelope[AlertResolvedV1].model_validate(alert_resolved_raw)

    assert env.payload.new_status == "CONFIRMED"


def test_reason_is_optional(alert_resolved_raw: dict) -> None:
    alert_resolved_raw["payload"].pop("reason")

    env = Envelope[AlertResolvedV1].model_validate(alert_resolved_raw)

    assert env.payload.reason is None
