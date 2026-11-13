from __future__ import annotations

from scoring.application.internal.outboundservices.rules.rule_engine import RuleEngine
from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.domain.model.valueobjects.risk_factor import RiskFactor
from scoring.domain.services.rule_catalog import Rule, RuleCatalog


class CatalogRuleEngine(RuleEngine):
    """
    Evaluates every rule from the catalog against the scoring command.
    Returns the summed score capped at 100 and the hits as ``RiskFactor``
    with ``source='rule'``. Adding a rule is a YAML edit; adding a new
    rule *type* means extending ``_check_rule``.
    """

    def __init__(self, catalog: RuleCatalog) -> None:
        self._catalog = catalog

    async def evaluate(
        self, command: ScoreTransactionCommand
    ) -> tuple[int, list[RiskFactor]]:
        rules = await self._catalog.active_rules()
        total = 0
        factors: list[RiskFactor] = []
        for rule in rules:
            if self._check_rule(rule, command):
                total += rule.points
                factors.append(
                    RiskFactor(
                        feature=rule.code,
                        weight=float(rule.points),
                        direction="increase",
                        source="rule",
                    )
                )
        return min(total, 100), factors

    def _check_rule(
        self, rule: Rule, command: ScoreTransactionCommand
    ) -> bool:
        code = rule.code
        params = rule.params
        features = command.extra_features

        if code == "atypical_amount":
            thresholds = params.get("thresholds", {})
            limit = thresholds.get(command.channel)
            return limit is not None and float(command.amount) > float(limit)

        if code == "high_risk_country":
            if command.country is None:
                return False
            return command.country in set(params.get("countries", []))

        if code == "unusual_hour":
            hour = command.occurred_at.hour
            start = int(params.get("hour_start", 0))
            end = int(params.get("hour_end", 6))
            return start <= hour < end

        if code == "new_device":
            feature = str(params.get("feature", "new_device"))
            return bool(features.get(feature, 0.0))

        if code == "velocity":
            feature = str(params.get("feature", "tx_count_last_5m"))
            threshold = float(params.get("threshold", 10))
            return float(features.get(feature, 0.0)) > threshold

        # Unknown rule code: skip silently. The YAML is the source of
        # truth; new rule types require a code change here.
        return False
