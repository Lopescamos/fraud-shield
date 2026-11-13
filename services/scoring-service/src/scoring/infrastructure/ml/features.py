from __future__ import annotations

import math

from scoring.domain.model.commands.score_transaction_command import (
    ScoreTransactionCommand,
)

FEATURE_NAMES: list[str] = [
    "amount_log",
    "hour_of_day",
    "tx_count_last_5m",
    "new_device",
    "amount_ratio_vs_avg",
]


def vectorize(command: ScoreTransactionCommand) -> list[float]:
    """
    Convert a ``ScoreTransactionCommand`` into the feature vector consumed
    by the ML adapters. Keep training and serving in sync: a change here
    forces a retrain and a new ``model_version``.
    """

    extra = command.extra_features
    return [
        math.log1p(float(command.amount)),
        float(command.occurred_at.hour),
        float(extra.get("tx_count_last_5m", 0.0)),
        float(extra.get("new_device", 0.0)),
        float(extra.get("amount_ratio_vs_avg", 1.0)),
    ]
