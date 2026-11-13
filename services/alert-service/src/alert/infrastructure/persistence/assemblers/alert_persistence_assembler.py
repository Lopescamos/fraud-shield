from __future__ import annotations

from alert.domain.model.aggregates.alert import Alert
from alert.domain.model.valueobjects.alert_status import AlertStatus
from alert.domain.model.valueobjects.priority import Priority
from alert.domain.model.valueobjects.risk_factor import RiskFactor
from alert.infrastructure.persistence.entities.alert_persistence_entity import (
    AlertPersistenceEntity,
)


class AlertPersistenceAssembler:
    @staticmethod
    def to_domain(entity: AlertPersistenceEntity) -> Alert:
        factors = [
            RiskFactor(
                feature=raw["feature"],
                weight=float(raw["weight"]),
                direction=raw["direction"],
                source=raw.get("source", "shap"),
            )
            for raw in (entity.factors or [])
        ]
        return Alert.restore(
            id=entity.id,
            transaction_id=entity.transaction_id,
            scoring_result_id=entity.scoring_result_id,
            account_id_hash=entity.account_id_hash,
            risk_score=entity.risk_score,
            level=entity.level,
            decision=entity.decision,
            model_version=entity.model_version,
            priority=Priority(entity.priority),
            status=AlertStatus(entity.status),
            factors=factors,
            analyst_id=entity.analyst_id,
            resolution=entity.resolution,
            opened_at=entity.opened_at,
            closed_at=entity.closed_at,
        )

    @staticmethod
    def to_persistence(alert: Alert) -> AlertPersistenceEntity:
        return AlertPersistenceEntity(
            id=alert.id,
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
                {
                    "feature": f.feature,
                    "weight": f.weight,
                    "direction": f.direction,
                    "source": f.source,
                }
                for f in alert.factors
            ],
            analyst_id=alert.analyst_id,
            resolution=alert.resolution,
            opened_at=alert.opened_at,
            closed_at=alert.closed_at,
        )
