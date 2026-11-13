from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ActiveModel:
    algorithm: str
    version: str
    metrics: dict[str, Any]


class ModelRegistry(Protocol):
    """
    Port that answers which model version is currently active for an
    algorithm (``xgboost``, ``isolation-forest``, …). The active model
    is the one whose row in ``scoring.model_registry`` has
    ``is_active=true``; if none exists, returns ``None`` and the service
    runs in degraded mode.
    """

    async def get_active(self, algorithm: str) -> ActiveModel | None: ...
