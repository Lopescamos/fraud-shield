from shared_contracts.alerts.v1 import AlertRaisedV1
from shared_contracts.envelope import Envelope


def test_roundtrip_ok(alert_raised_raw: dict) -> None:
    env = Envelope[AlertRaisedV1].model_validate(alert_raised_raw)

    assert env.payload.severity == "HIGH"
    assert env.payload.score == 87

    dumped = env.model_dump(mode="json")
    assert dumped["payload"]["level"] == "HIGH"


def test_tolerates_unknown_fields(alert_raised_raw: dict) -> None:
    alert_raised_raw["payload"]["channel_hint"] = "WEB"

    env = Envelope[AlertRaisedV1].model_validate(alert_raised_raw)

    assert env.payload.severity == "HIGH"
