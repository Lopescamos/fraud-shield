"""
Puerta de calidad para los modelos de scoring (ADR-007, RNF-23). Toma
un XGBoost ya entrenado y una muestra de validacion, calcula PR-AUC y
recall, y falla con exit 1 si cualquiera de los dos cae por debajo del
umbral configurado.

Uso:
    poetry run python scripts/evaluate_model.py \
        --model data/models/xgb/xgb-abc.json \
        --data data/raw/validation.csv \
        --pr-auc-min 0.60 --recall-min 0.75
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score, precision_score, recall_score

FEATURE_COLUMNS = [
    "amount_log",
    "hour_of_day",
    "tx_count_last_5m",
    "new_device",
    "amount_ratio_vs_avg",
]


def _load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def evaluate(model_path: Path, data_path: Path) -> dict:
    booster = xgb.Booster()
    booster.load_model(str(model_path))

    df = _load(data_path)
    x = df[FEATURE_COLUMNS]
    y = df["label"].astype(int)
    proba = booster.predict(xgb.DMatrix(x))
    pred = (proba >= 0.5).astype(int)

    return {
        "pr_auc": float(average_precision_score(y, proba)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "size": int(len(y)),
        "positives": int((y == 1).sum()),
    }


def main(args: argparse.Namespace) -> int:
    metrics = evaluate(Path(args.model), Path(args.data))
    report = {
        "model": str(args.model),
        "data": str(args.data),
        "thresholds": {"pr_auc_min": args.pr_auc_min, "recall_min": args.recall_min},
        "metrics": metrics,
        "passed": bool(
            metrics["pr_auc"] >= args.pr_auc_min
            and metrics["recall"] >= args.recall_min
        ),
    }
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

    if not report["passed"]:
        print("evaluation failed: thresholds not met", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--pr-auc-min", type=float, default=0.60)
    parser.add_argument("--recall-min", type=float, default=0.75)
    parser.add_argument("--report", default=None)
    sys.exit(main(parser.parse_args()))
