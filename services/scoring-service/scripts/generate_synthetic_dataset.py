"""
Genera un dataset sintético de transacciones para probar los scripts
de training sin tener que esperar a tener datos reales de producción.

Las features son exactamente las que ``scoring.infrastructure.ml.features.vectorize``
produce: amount_log, hour_of_day, tx_count_last_5m, new_device,
amount_ratio_vs_avg. ``label`` es 1 cuando la combinación huele a fraude:
alto monto + nuevo dispositivo + alta velocidad, con algo de ruido para
que el modelo no sea trivialmente separable.

Uso:
    poetry run python scripts/generate_synthetic_dataset.py \
        --out data/raw/synthetic.csv --rows 20000 --seed 42
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "amount_log",
    "hour_of_day",
    "tx_count_last_5m",
    "new_device",
    "amount_ratio_vs_avg",
]


def generate(rows: int, fraud_rate: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    amount = rng.lognormal(mean=4.5, sigma=1.2, size=rows)
    amount_log = np.log1p(amount)
    hour_of_day = rng.integers(0, 24, size=rows)
    tx_count = rng.poisson(lam=1.8, size=rows)
    new_device = rng.binomial(n=1, p=0.08, size=rows)
    amount_ratio = rng.gamma(shape=2.0, scale=0.8, size=rows)

    # A hidden linear-ish rule the model is meant to recover.
    logits = (
        -4.5
        + 0.9 * (amount_log - math.log1p(100))
        + 0.6 * new_device
        + 0.4 * (tx_count > 10).astype(float)
        + 0.5 * (amount_ratio - 1.0)
        + 0.3 * ((hour_of_day < 6).astype(float))
    )
    base_prob = 1.0 / (1.0 + np.exp(-logits))
    # Keep the global fraud rate close to the requested value.
    scale = fraud_rate / max(base_prob.mean(), 1e-6)
    prob = np.clip(base_prob * scale, 0.0, 0.5)
    label = rng.binomial(n=1, p=prob)

    occurred_at = pd.date_range("2026-10-01", periods=rows, freq="min")
    return pd.DataFrame(
        {
            "occurred_at": occurred_at,
            "amount_log": amount_log,
            "hour_of_day": hour_of_day.astype(float),
            "tx_count_last_5m": tx_count.astype(float),
            "new_device": new_device.astype(float),
            "amount_ratio_vs_avg": amount_ratio,
            "label": label.astype(int),
        }
    )


def main(args: argparse.Namespace) -> None:
    df = generate(args.rows, args.fraud_rate, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    positives = int(df["label"].sum())
    print(
        f"wrote {len(df)} rows to {out} with {positives} positives "
        f"({positives / len(df):.2%})"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--rows", type=int, default=20_000)
    parser.add_argument("--fraud-rate", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=42)
    main(parser.parse_args())
