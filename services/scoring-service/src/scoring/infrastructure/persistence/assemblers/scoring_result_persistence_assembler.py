from __future__ import annotations

from decimal import Decimal

from scoring.domain.model.aggregates.scoring_result import ScoringResult
from scoring.domain.model.valueobjects.decision import Decision
from scoring.domain.model.valueobjects.model_version import ModelVersion
from scoring.domain.model.valueobjects.risk_factor import RiskFactor
from scoring.domain.model.valueobjects.risk_score import RiskScore
from scoring.infrastructure.persistence.entities.scoring_result_persistence_entity import (
    ScoringResultPersistenceEntity,
)


class ScoringResultPersistenceAssembler:
    """Maps between the SQLAlchemy entity and the aggregate (via restore)."""

    @staticmethod
    def to_domain(entity: ScoringResultPersistenceEntity) -> ScoringResult:
        factors = [
            RiskFactor(
                feature=raw["feature"],
                weight=float(raw["weight"]),
                direction=raw["direction"],
                source=raw.get("source", "shap"),
            )
            for raw in (entity.factors or [])
        ]
        return ScoringResult.restore(
            id=entity.id,
            transaction_id=entity.transaction_id,
            account_id_hash=entity.account_id_hash,
            score=RiskScore(float(entity.score)),
            decision=Decision(entity.decision),
            level=entity.level,
            rules_score=entity.rules_score,
            xgb_probability=entity.xgb_probability,
            iforest_anomaly=entity.iforest_anomaly,
            model_version=ModelVersion(entity.model_version),
            degraded_mode=entity.degraded_mode,
            factors=factors,
            occurred_at=entity.occurred_at,
        )

    @staticmethod
    def to_persistence(result: ScoringResult) -> ScoringResultPersistenceEntity:
        return ScoringResultPersistenceEntity(
            id=result.id,
            transaction_id=result.transaction_id,
            account_id_hash=result.account_id_hash,
            score=result.score.as_int(),
            level=result.level,
            decision=result.decision.value,
            rules_score=result.rules_score,
            xgb_probability=Decimal(str(result.xgb_probability)),
            iforest_anomaly=Decimal(str(result.iforest_anomaly)),
            degraded_mode=result.degraded_mode,
            model_version=result.model_version.value,
            factors=[
                {
                    "feature": f.feature,
                    "weight": f.weight,
                    "direction": f.direction,
                    "source": f.source,
                }
                for f in result.factors
            ],
            occurred_at=result.occurred_at,
        )
