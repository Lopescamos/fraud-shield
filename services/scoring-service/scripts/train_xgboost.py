"""
Entrena un XGBoost sobre el dataset de transacciones y guarda el modelo
en ``data/models/xgb/``. Produce ``xgb-<version>.json`` + metadata con
las metricas y la lista de features. Reproducible con ``--seed 42``.

Uso:
    poetry run python scripts/train_xgboost.py \
        --data data/raw/synthetic.csv --out data/models/xgb/

La forma de la metadata es la que ``model_registry`` espera: algorithm,
version, metrics (pr_auc, precision, recall), features, trained_at.
"""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score, precision_score, recall_score
from sklearn.model_selection import TimeSeriesSplit

FEATURE_COLUMNS = [
    "amount_log",
    "hour_of_day",
    "tx_count_last_5m",
    "new_device",
    "amount_ratio_vs_avg",
]


def _load(path: Path) -> pd.DataFrame:
    # Only CSV for now: pyarrow is painful to install on Windows CI.
    return pd.read_csv(path)


def train(df: pd.DataFrame, seed: int) -> tuple[xgb.Booster, dict]:
    df = df.sort_values("occurred_at") if "occurred_at" in df.columns else df
    x = df[FEATURE_COLUMNS]
    y = df["label"].astype(int)

    pos = max(int((y == 1).sum()), 1)
    neg = int((y == 0).sum())
    scale_pos_weight = neg / pos

    splits = list(TimeSeriesSplit(n_splits=5).split(x))
    train_idx, test_idx = splits[-1]
    x_tr, x_te = x.iloc[train_idx], x.iloc[test_idx]
    y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]

    booster = xgb.train(
        params={
            "objective": "binary:logistic",
            "eval_metric": "aucpr",
            "scale_pos_weight": scale_pos_weight,
            "max_depth": 6,
            "eta": 0.1,
            "seed": seed,
        },
        dtrain=xgb.DMatrix(x_tr, label=y_tr),
        num_boost_round=200,
        evals=[(xgb.DMatrix(x_te, label=y_te), "val")],
        early_stopping_rounds=20,
        verbose_eval=False,
    )

    proba = booster.predict(xgb.DMatrix(x_te))
    pred = (proba >= 0.5).astype(int)
    metrics = {
        "pr_auc": float(average_precision_score(y_te, proba)),
        "precision": float(precision_score(y_te, pred, zero_division=0)),
        "recall": float(recall_score(y_te, pred, zero_division=0)),
        "test_positives": int((y_te == 1).sum()),
        "test_size": int(len(y_te)),
    }
    return booster, metrics


def main(args: argparse.Namespace) -> None:
    df = _load(Path(args.data))
    np.random.seed(args.seed)

    booster, metrics = train(df, seed=args.seed)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    version = args.version or uuid.uuid4().hex[:12]
    model_path = out_dir / f"xgb-{version}.json"
    metadata_path = out_dir / f"xgb-{version}.metadata.json"

    booster.save_model(str(model_path))
    metadata = {
        "algorithm": "xgboost",
        "version": version,
        "features": FEATURE_COLUMNS,
        "metrics": metrics,
        "trained_at": datetime.now(UTC).isoformat(),
        "seed": args.seed,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(
        f"saved XGBoost model {version} -> {model_path} "
        f"(pr_auc={metrics['pr_auc']:.3f}, recall={metrics['recall']:.3f})"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--version", default=None)
    main(parser.parse_args())
