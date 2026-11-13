from __future__ import annotations

from alert.domain.model.aggregates.alert import Alert
from alert.interfaces.rest.resources.alert_resource import (
    AlertResource,
    RiskFactorResource,
)


class AlertResourceFromEntityAssembler:
    @staticmethod
    def to_resource(alert: Alert) -> AlertResource:
        return AlertResource(
            alert_id=alert.id,
            transaction_id=alert.transaction_id,
            scoring_result_id=alert.scoring_result_id,
            account_id_hash=alert.account_id_hash,
            risk_score=alert.risk_score,
            level=alert.level,
            decision=alert.decision,
            model_version=alert.model_version,
            priority=alert.priority.value,
            status=alert.status.value,
            factors=[
                RiskFactorResource(
                    feature=f.feature,
                    weight=f.weight,
                    direction=f.direction,
                    source=f.source,
                )
                for f in alert.factors
            ],
            analyst_id=alert.analyst_id,
            resolution=alert.resolution,
            opened_at=alert.opened_at,
            closed_at=alert.closed_at,
        )
