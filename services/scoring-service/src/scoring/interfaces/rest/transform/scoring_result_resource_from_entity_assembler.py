from __future__ import annotations

from scoring.domain.model.aggregates.scoring_result import ScoringResult
from scoring.interfaces.rest.resources.scoring_result_resource import (
    RiskFactorResource,
    ScoringResultResource,
)


class ScoringResultResourceFromEntityAssembler:
    @staticmethod
    def to_resource(result: ScoringResult) -> ScoringResultResource:
        return ScoringResultResource(
            scoring_result_id=result.id,
            transaction_id=result.transaction_id,
            account_id_hash=result.account_id_hash,
            score=result.score.as_int(),
            level=result.level,
            decision=result.decision.value,
            rules_score=result.rules_score,
            xgb_probability=result.xgb_probability,
            iforest_anomaly=result.iforest_anomaly,
            degraded_mode=result.degraded_mode,
            model_version=result.model_version.value,
            factors=[
                RiskFactorResource(
                    feature=f.feature,
                    weight=f.weight,
                    direction=f.direction,
                    source=f.source,
                )
                for f in result.factors
            ],
            occurred_at=result.occurred_at,
        )
