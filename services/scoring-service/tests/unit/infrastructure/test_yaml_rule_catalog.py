from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)
from scoring.infrastructure.rules.catalog_rule_engine import CatalogRuleEngine
from scoring.infrastructure.rules.yaml_rule_catalog import YamlRuleCatalog


@pytest.fixture
def catalog() -> YamlRuleCatalog:
    path = (
        Path(__file__).resolve().parents[3]
        / "src/scoring/infrastructure/rules/rules.yaml"
    )
    return YamlRuleCatalog(path)


def _cmd(
    *,
    amount: Decimal = Decimal("100.00"),
    channel: str = "WEB",
    country: str | None = "PE",
    hour: int = 13,
    features: dict[str, float] | None = None,
) -> ScoreTransactionCommand:
    return ScoreTransactionCommand(
        transaction_id=uuid4(),
        account_id_hash="a" * 64,
        amount=amount,
        currency="PEN",
        channel=channel,
        occurred_at=datetime(2026, 11, 13, hour, 0, tzinfo=UTC),
        country=country,
        device_id="device-1",
        extra_features=features or {},
    )


@pytest.mark.asyncio
async def test_catalog_loads_rules_from_yaml(catalog: YamlRuleCatalog) -> None:
    rules = await catalog.active_rules()
    codes = {r.code for r in rules}
    assert codes >= {"atypical_amount", "high_risk_country", "unusual_hour",
                     "new_device", "velocity"}


@pytest.mark.asyncio
async def test_catalog_is_cached(catalog: YamlRuleCatalog) -> None:
    a = await catalog.active_rules()
    b = await catalog.active_rules()
    assert len(a) == len(b)


@pytest.mark.asyncio
async def test_rule_engine_scores_nothing_for_safe_tx(
    catalog: YamlRuleCatalog,
) -> None:
    engine = CatalogRuleEngine(catalog)
    score, factors = await engine.evaluate(_cmd(amount=Decimal("50.00")))
    assert score == 0
    assert factors == []


@pytest.mark.asyncio
async def test_atypical_amount_trips_over_channel_threshold(
    catalog: YamlRuleCatalog,
) -> None:
    engine = CatalogRuleEngine(catalog)
    score, factors = await engine.evaluate(
        _cmd(channel="WEB", amount=Decimal("5000.00"))
    )
    codes = [f.feature for f in factors]
    assert "atypical_amount" in codes
    assert score >= 25


@pytest.mark.asyncio
async def test_high_risk_country_and_unusual_hour_stack(
    catalog: YamlRuleCatalog,
) -> None:
    engine = CatalogRuleEngine(catalog)
    score, factors = await engine.evaluate(
        _cmd(country="NG", hour=3, amount=Decimal("100.00"))
    )
    codes = [f.feature for f in factors]
    assert "high_risk_country" in codes
    assert "unusual_hour" in codes
    assert score == 40


@pytest.mark.asyncio
async def test_velocity_rule_trips_above_threshold(
    catalog: YamlRuleCatalog,
) -> None:
    engine = CatalogRuleEngine(catalog)
    score, factors = await engine.evaluate(
        _cmd(features={"tx_count_last_5m": 15.0})
    )
    assert "velocity" in [f.feature for f in factors]
    assert score >= 30


@pytest.mark.asyncio
async def test_score_is_capped_at_100(catalog: YamlRuleCatalog) -> None:
    engine = CatalogRuleEngine(catalog)
    score, _ = await engine.evaluate(
        _cmd(
            country="NG",
            hour=3,
            amount=Decimal("5000.00"),
            features={"tx_count_last_5m": 20.0, "new_device": 1.0},
        )
    )
    assert score == 100
