from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class AccountId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("[AccountId] value cannot be empty")

    def hashed(self) -> str:
        return sha256(self.value.encode()).hexdigest()
