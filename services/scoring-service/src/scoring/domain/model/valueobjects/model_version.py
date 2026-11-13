from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelVersion:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("[ModelVersion] value cannot be empty")

    @classmethod
    def rules_only(cls) -> ModelVersion:
        return cls("rules-only")
