from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class Rule:
    code: str
    description: str
    points: int
    params: dict[str, Any]


class RuleCatalog(Protocol):
    async def active_rules(self) -> list[Rule]: ...
