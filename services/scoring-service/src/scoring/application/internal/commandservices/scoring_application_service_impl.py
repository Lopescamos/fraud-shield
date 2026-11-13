from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from scoring.application.internal.outboundservices.rules.rule_engine import RuleEngine
from scoring.domain.model.aggregates.scoring_result import ScoringResult
from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.domain.model.valueobjects.model_version import ModelVersion
from scoring.domain.model.valueobjects.risk_factor import RiskFactor
from scoring.domain.model.valueobjects.risk_score import RiskScore
from scoring.domain.repositories.scoring_result_repository import (
    ScoringResultRepository,
)
from scoring.domain.services.explainer import Explainer
from scoring.domain.services.risk_model import RiskModel
from scoring.kernel.application.result import (
    ApplicationError,
    Failure,
    Result,
    Success,
)
from scoring.kernel.application.transactional import transactional

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ScoringWeights:
    """Weights used to combine rules, xgboost and isolation forest scores.
    They sum to 1.0 in the default config but the service tolerates any
    non-negative combination (ADR-007)."""

    rules: float = 0.4
    xgb: float = 0.4
    iforest: float = 0.2


class ScoringApplicationServiceImpl:
    def __init__(
        self,
        session_factory: Any,
        repository_builder: Callable[[Any], ScoringResultRepository],
        rule_engine: RuleEngine,
        xgb_model: RiskModel,
        iforest_model: RiskModel,
        explainer: Explainer,
        weights: ScoringWeights | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._repository_builder = repository_builder
        self._rule_engine = rule_engine
        self._xgb_model = xgb_model
        self._iforest_model = iforest_model
        self._explainer = explainer
        self._weights = weights or ScoringWeights()
        self._session: Any = None

    @transactional
    async def handle(
        self,
        command: ScoreTransactionCommand,
        idempotency_key: str | None = None,
    ) -> Result[UUID, ApplicationError]:
        repository = self._repository_builder(self._session)

        existing = await repository.find_by_transaction_id(command.transaction_id)
        if existing is not None:
            return Success(existing.id)

        try:
            rules_score, rule_factors = await self._rule_engine.evaluate(command)
        except Exception as exc:
            logger.exception("rule-engine-failed")
            return Failure(
                ApplicationError.unexpected("evaluate-rules", str(exc))
            )

        xgb_available = self._xgb_model.is_available()
        iforest_available = self._iforest_model.is_available()
        degraded = not (xgb_available and iforest_available)

        p_xgb = 0.0
        a_iso = 0.0
        shap_factors: list[RiskFactor] = []
        model_version = ModelVersion.rules_only()

        if xgb_available:
            try:
                p_xgb = await self._xgb_model.score(command)
                model_version = ModelVersion(self._xgb_model.version())
            except Exception:
                logger.exception("xgb-scoring-failed-degrading")
                p_xgb = 0.0
                degraded = True
                model_version = ModelVersion.rules_only()

        if iforest_available:
            try:
                a_iso = await self._iforest_model.score(command)
            except Exception:
                logger.exception("iforest-scoring-failed-degrading")
                a_iso = 0.0
                degraded = True

        if not degraded and self._explainer.is_available():
            try:
                shap_factors = await self._explainer.top_factors(command, top_n=3)
            except Exception:
                logger.exception("explainer-failed-dropping-shap")
                shap_factors = []

        combined = (
            self._weights.rules * rules_score
            + self._weights.xgb * 100.0 * float(p_xgb)
            + self._weights.iforest * 100.0 * float(a_iso)
        )
        combined = max(0.0, min(100.0, combined))

        try:
            score = RiskScore(combined)
        except ValueError as exc:
            return Failure(ApplicationError.validation_error("score", str(exc)))

        factors = list(rule_factors) + list(shap_factors)

        try:
            aggregate = ScoringResult.register(
                transaction_id=command.transaction_id,
                account_id_hash=command.account_id_hash,
                score=score,
                rules_score=int(rules_score),
                xgb_probability=Decimal(f"{float(p_xgb):.6f}"),
                iforest_anomaly=Decimal(f"{float(a_iso):.6f}"),
                model_version=model_version,
                degraded_mode=degraded,
                factors=factors,
                occurred_at=datetime.now(UTC),
            )
        except ValueError as exc:
            return Failure(ApplicationError.validation_error("scoring-result", str(exc)))

        try:
            saved = await repository.save(aggregate)
        except Exception as exc:
            return Failure(ApplicationError.unexpected("save-scoring-result", str(exc)))

        if idempotency_key is not None:
            logger.info(
                "scoring-idempotency-key-received",
                extra={"idempotency_key": idempotency_key, "scoring_result_id": str(saved.id)},
            )

        return Success(saved.id)
