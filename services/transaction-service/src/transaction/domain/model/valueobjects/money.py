from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("[Money] amount must be greater than zero")
        if len(self.currency) != 3:
            raise ValueError("[Money] currency must be a 3-letter ISO code")
