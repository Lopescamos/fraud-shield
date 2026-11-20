from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _import_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_script_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_synthetic_dataset_is_deterministic(tmp_path) -> None:
    gen = _import_script("generate_synthetic_dataset")
    df1 = gen.generate(rows=500, fraud_rate=0.1, seed=42)
    df2 = gen.generate(rows=500, fraud_rate=0.1, seed=42)
    assert df1.equals(df2)
    assert set(gen.FEATURE_COLUMNS).issubset(set(df1.columns))
    assert df1["label"].between(0, 1).all()


def test_train_xgboost_produces_model_and_metadata(tmp_path) -> None:
    gen = _import_script("generate_synthetic_dataset")
    df = gen.generate(rows=2_000, fraud_rate=0.1, seed=42)
    data_path = tmp_path / "data.csv"
    df.to_csv(data_path, index=False)

    tr = _import_script("train_xgboost")
    booster, metrics = tr.train(df, seed=42)
    assert set(metrics.keys()) >= {"pr_auc", "precision", "recall"}
    assert 0.0 <= metrics["pr_auc"] <= 1.0

    out = tmp_path / "models"
    out.mkdir()
    model_path = out / "xgb-test.json"
    booster.save_model(str(model_path))
    assert model_path.exists()
    assert model_path.stat().st_size > 0


def test_train_isolation_forest_returns_metrics() -> None:
    gen = _import_script("generate_synthetic_dataset")
    df = gen.generate(rows=2_000, fraud_rate=0.1, seed=42)

    tr = _import_script("train_isolation_forest")
    model, metrics = tr.train(df, seed=42, contamination=0.05)
    assert hasattr(model, "decision_function")
    assert 0.0 <= metrics["pr_auc"] <= 1.0


def test_evaluate_model_gate_passes_and_fails(tmp_path) -> None:
    gen = _import_script("generate_synthetic_dataset")
    df = gen.generate(rows=2_000, fraud_rate=0.1, seed=42)
    data_path = tmp_path / "data.csv"
    df.to_csv(data_path, index=False)

    tr = _import_script("train_xgboost")
    booster, _ = tr.train(df, seed=42)
    model_path = tmp_path / "xgb-test.json"
    booster.save_model(str(model_path))

    ev = _import_script("evaluate_model")
    metrics = ev.evaluate(model_path, data_path)
    assert 0.0 <= metrics["pr_auc"] <= 1.0
    assert 0.0 <= metrics["recall"] <= 1.0


@pytest.mark.parametrize(
    "pr_auc_min, recall_min, expected_exit",
    [(0.0, 0.0, 0), (0.999, 0.999, 1)],
)
def test_evaluate_model_cli_exit_codes(
    tmp_path, pr_auc_min, recall_min, expected_exit
) -> None:
    # Prepare a tiny model + data.
    gen = _import_script("generate_synthetic_dataset")
    df = gen.generate(rows=1_500, fraud_rate=0.1, seed=42)
    data_path = tmp_path / "data.csv"
    df.to_csv(data_path, index=False)

    tr = _import_script("train_xgboost")
    booster, _ = tr.train(df, seed=42)
    model_path = tmp_path / "xgb.json"
    booster.save_model(str(model_path))

    ev = _import_script("evaluate_model")
    args = type(
        "A",
        (),
        {
            "model": str(model_path),
            "data": str(data_path),
            "pr_auc_min": pr_auc_min,
            "recall_min": recall_min,
            "report": None,
        },
    )()
    assert ev.main(args) == expected_exit
