"""
Entrena un IsolationForest para detectar anomalias y lo serializa con
joblib en ``data/models/iforest/``. No supervisado: usa solo las filas
con label=0 para fitear y evalua PR-AUC usando el score normalizado
(mas negativo = mas anomalo).

Uso:
    poetry run python scripts/train_isolation_forest.py \
        --data data/raw/synthetic.csv --out data/models/iforest/
"""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score

FEATURE_COLUMNS = [
    "amount_log",
    "hour_of_day",
    "tx_count_last_5m",
    "new_device",
    "amount_ratio_vs_avg",
]


def _load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def train(df: pd.DataFrame, seed: int, contamination: float) -> tuple[IsolationForest, dict]:
    x = df[FEATURE_COLUMNS]
    y = df["label"].astype(int)

    # Fit on negatives only. With that we cheat a little less on the
    # evaluation signal.
    x_fit = x[y == 0]
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=seed,
    )
    model.fit(x_fit)

    raw = model.decision_function(x)  # higher = more normal
    anomaly = 0.5 - raw  # same transform used at runtime
    pr_auc = float(average_precision_score(y, anomaly))
    return model, {
        "pr_auc": pr_auc,
        "fit_size": int(len(x_fit)),
        "eval_size": int(len(x)),
        "contamination": contamination,
    }


def main(args: argparse.Namespace) -> None:
    df = _load(Path(args.data))
    np.random.seed(args.seed)

    model, metrics = train(df, seed=args.seed, contamination=args.contamination)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    version = args.version or uuid.uuid4().hex[:12]
    model_path = out_dir / f"iforest-{version}.joblib"
    metadata_path = out_dir / f"iforest-{version}.metadata.json"

    joblib.dump(model, model_path)
    metadata = {
        "algorithm": "isolation-forest",
        "version": version,
        "features": FEATURE_COLUMNS,
        "metrics": metrics,
        "trained_at": datetime.now(UTC).isoformat(),
        "seed": args.seed,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(
        f"saved IsolationForest model {version} -> {model_path} "
        f"(pr_auc={metrics['pr_auc']:.3f})"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--contamination", type=float, default=0.03)
    parser.add_argument("--version", default=None)
    main(parser.parse_args())
