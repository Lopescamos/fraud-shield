from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from scoring.domain.model.events.scoring_result_registered_event import (
    ScoringResultRegisteredEvent,
)
from scoring.domain.model.valueobjects.decision import Decision, level_from_score
from scoring.domain.model.valueobjects.model_version import ModelVersion
from scoring.domain.model.valueobjects.risk_factor import RiskFactor
from scoring.domain.model.valueobjects.risk_score import RiskScore
from scoring.kernel.domain import AbstractDomainAggregateRoot
from scoring.kernel.ids import Ids


@dataclass
class ScoringResult(AbstractDomainAggregateRoot):
    id: UUID
    transaction_id: UUID
    account_id_hash: str
    score: RiskScore
    decision: Decision
    level: str
    rules_score: int
    xgb_probability: Decimal
    iforest_anomaly: Decimal
    model_version: ModelVersion
    degraded_mode: bool
    factors: list[RiskFactor] = field(default_factory=list)
    occurred_at: datetime | None = None

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        transaction_id: UUID,
        account_id_hash: str,
        score: RiskScore,
        decision: Decision,
        level: str,
        rules_score: int,
        xgb_probability: Decimal,
        iforest_anomaly: Decimal,
        model_version: ModelVersion,
        degraded_mode: bool,
        factors: list[RiskFactor],
        occurred_at: datetime | None,
    ) -> ScoringResult:
        return cls(
            id=id,
            transaction_id=transaction_id,
            account_id_hash=account_id_hash,
            score=score,
            decision=decision,
            level=level,
            rules_score=rules_score,
            xgb_probability=xgb_probability,
            iforest_anomaly=iforest_anomaly,
            model_version=model_version,
            degraded_mode=degraded_mode,
            factors=list(factors),
            occurred_at=occurred_at,
        )

    @classmethod
    def register(
        cls,
        *,
        transaction_id: UUID,
        account_id_hash: str,
        score: RiskScore,
        rules_score: int,
        xgb_probability: Decimal,
        iforest_anomaly: Decimal,
        model_version: ModelVersion,
        degraded_mode: bool,
        factors: list[RiskFactor],
        occurred_at: datetime,
    ) -> ScoringResult:
        score_int = score.as_int()
        decision = Decision.from_score(score_int)
        level = level_from_score(score_int)
        result = cls(
            id=Ids.new_id(),
            transaction_id=transaction_id,
            account_id_hash=account_id_hash,
            score=score,
            decision=decision,
            level=level,
            rules_score=rules_score,
            xgb_probability=xgb_probability,
            iforest_anomaly=iforest_anomaly,
            model_version=model_version,
            degraded_mode=degraded_mode,
            factors=list(factors),
            occurred_at=occurred_at,
        )
        result._register_event(
            ScoringResultRegisteredEvent(
                scoring_result_id=result.id,
                transaction_id=transaction_id,
                account_id_hash=account_id_hash,
                score=score_int,
                level=level,
                decision=decision.value,
                rules_score=rules_score,
                xgb_probability=xgb_probability,
                iforest_anomaly=iforest_anomaly,
                degraded_mode=degraded_mode,
                model_version=model_version.value,
                occurred_at=occurred_at,
            )
        )
        return result
