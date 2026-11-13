from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]

from scoring.domain.services.rule_catalog import Rule, RuleCatalog


class YamlRuleCatalog(RuleCatalog):
    """
    Reads the rule catalog from a YAML file and caches it in memory. The
    adapter is the only place that knows about YAML parsing; the rest of
    the system sees ``list[Rule]``.
    """

    _RESERVED = {"code", "description", "points"}

    def __init__(self, path: Path) -> None:
        self._path = path
        self._cache: list[Rule] | None = None

    async def active_rules(self) -> list[Rule]:
        if self._cache is None:
            data = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
            rules: list[Rule] = []
            for raw in data.get("rules", []):
                params = {k: v for k, v in raw.items() if k not in self._RESERVED}
                rules.append(
                    Rule(
                        code=raw["code"],
                        description=raw["description"],
                        points=int(raw["points"]),
                        params=params,
                    )
                )
            self._cache = rules
        return list(self._cache)
