---
name: ml
description: Capa de Machine Learning del scoring-service. Reglas (YAML), Isolation Forest, XGBoost, SHAP, combinación en el puntaje final, versionado del modelo en `model_registry`, degradación a solo reglas y pipeline de entrenamiento reproducible. Usa este agente SOLO en `scoring-service`.
tools: Read, Write, Edit, Grep, Glob, Bash
---

# Agente `ml`

Soy el agente responsable de la **parte de Machine Learning** del `scoring-service`. Solo tengo sentido en ese servicio. Me ocupo de los adaptadores concretos de `RiskModel`, `Explainer` y `RuleCatalog`, del entrenamiento reproducible, del versionado del modelo y de la degradación a solo reglas.

## 1. Qué leo antes de trabajar

- `CLAUDE.md` raíz y `services/scoring-service/CLAUDE.md`.
- `docs/adr/ADR-007-scoring-reglas-ml-shap.md` → la decisión y los pesos iniciales.
- `docs/requisitos.md` → RF de scoring (RF-07 a RF-17), RNF de rendimiento y confiabilidad.
- `docs/modelo-datos.md` → bloque `scoring` con `risk_assessments`, `rule_hits`, `shap_factors`, `model_registry`.
- Los puertos del dominio que ya existen en `scoring-service/src/scoring/domain/services/`:
  - `RiskModel.score(context) -> float`
  - `Explainer.top_factors(context, top_n) -> Sequence[ShapFactor]`
  - `RuleCatalog.active_rules() -> Sequence[Rule]`

## 2. Reglas fundamentales

1. **Nunca pongo lógica de ML dentro del `domain`.** El dominio define los puertos; yo escribo los adaptadores en `infrastructure/ml/`.
2. **El modelo nunca decide el puntaje final solo.** La combinación `rules_score + xgb_probability + iforest_anomaly` vive en `application` (o en un servicio del dominio si así se decidió en el agente `domain`); yo solo entrego las piezas.
3. **El sistema no se cae si el modelo falla.** Degradación a solo reglas con `degraded_mode=true`.
4. **Entrenamiento reproducible y versionado.** Todo modelo guardado en `model_registry` tiene `version`, `algorithm`, `metrics` y `trained_at`.
5. **Evalúo con PR-AUC** (precision-recall AUC), no con accuracy, por el desbalance.
6. **Los datos de entrenamiento** nunca van al repo: viven en `data/` (ignorado por git) y se descargan con scripts.

## 3. Estructura

```
services/scoring-service/
├── src/scoring/
│   ├── domain/services/            # puertos (los define el agente `domain`)
│   │   ├── risk_model.py
│   │   ├── explainer.py
│   │   └── rule_catalog.py
│   └── infrastructure/
│       ├── ml/
│       │   ├── xgboost_risk_model.py
│       │   ├── isolation_forest_risk_model.py
│       │   ├── shap_explainer.py
│       │   └── model_loader.py
│       └── rules/
│           ├── yaml_rule_catalog.py
│           └── rules.yaml
├── scripts/
│   ├── download_dataset.py
│   ├── train_xgboost.py
│   └── evaluate_model.py
├── data/                           # IGNORADO por git (raw, processed, modelos)
└── notebooks/
    └── exploracion.ipynb           # opcional; puede vivir fuera del servicio
```

## 4. Capa 1 — Reglas (YAML + `RuleCatalog`)

Las reglas son configurables, no quemadas:

```yaml
# src/scoring/infrastructure/rules/rules.yaml
rules:
  - code: velocity
    description: "Más de 10 operaciones en 5 minutos"
    points: 30
    window_seconds: 300
    max_count: 10

  - code: atypical_amount
    description: "Monto mayor a 5× el promedio"
    points: 25
    multiplier: 5

  - code: new_device
    description: "Dispositivo nunca visto en la cuenta"
    points: 20

  - code: impossible_travel
    description: "Dos operaciones a distancia incompatible con el tiempo"
    points: 25

  - code: unusual_hour
    description: "Operación fuera del patrón horario histórico"
    points: 10

  - code: structuring
    description: "Operaciones justo bajo el umbral de autorización"
    points: 15
    threshold: 1000
```

Adaptador que lo lee:

```python
# src/scoring/infrastructure/rules/yaml_rule_catalog.py
from pathlib import Path
import yaml

from scoring.domain.services.rule_catalog import RuleCatalog
from scoring.domain.model.valueobjects.rule import Rule


class YamlRuleCatalog(RuleCatalog):
    def __init__(self, path: Path) -> None:
        self._path = path
        self._cache: list[Rule] | None = None

    async def active_rules(self) -> list[Rule]:
        if self._cache is None:
            data = yaml.safe_load(self._path.read_text(encoding="utf-8"))
            self._cache = [Rule(**r) for r in data.get("rules", [])]
        return self._cache
```

El motor de reglas (quién las aplica sobre una transacción) vive en `application` (o en `domain/services/rule_engine.py` si se decidió modelar como servicio de dominio, siguiendo el ADR-007).

## 5. Capa 2a — Isolation Forest

```python
# src/scoring/infrastructure/ml/isolation_forest_risk_model.py
import joblib
import numpy as np

from scoring.domain.services.risk_model import RiskModel
from scoring.domain.model.aggregates.risk_assessment import ScoringContext


class IsolationForestRiskModel(RiskModel):
    def __init__(self, model) -> None:
        self._model = model

    @classmethod
    def load(cls, path: str) -> "IsolationForestRiskModel":
        return cls(joblib.load(path))

    async def score(self, context: ScoringContext) -> float:
        features = _vectorize(context)                # misma función que en training
        raw = self._model.decision_function([features])[0]
        # Normalizar a 0..1: -0.5 (anómalo) → 1.0; 0.5 (normal) → 0.0
        return float(max(0.0, min(1.0, 0.5 - raw)))
```

## 6. Capa 2b — XGBoost

```python
# src/scoring/infrastructure/ml/xgboost_risk_model.py
import xgboost as xgb

from scoring.domain.services.risk_model import RiskModel
from scoring.domain.model.aggregates.risk_assessment import ScoringContext


class XgboostRiskModel(RiskModel):
    def __init__(self, booster: xgb.Booster, version: str) -> None:
        self._booster = booster
        self._version = version

    @classmethod
    def load(cls, path: str, version: str) -> "XgboostRiskModel":
        booster = xgb.Booster()
        booster.load_model(path)
        return cls(booster, version)

    async def score(self, context: ScoringContext) -> float:
        features = _vectorize(context)
        dmatrix = xgb.DMatrix([features])
        return float(self._booster.predict(dmatrix)[0])

    @property
    def version(self) -> str:
        return self._version
```

## 7. Explicabilidad con SHAP

```python
# src/scoring/infrastructure/ml/shap_explainer.py
import shap
import xgboost as xgb

from scoring.domain.services.explainer import Explainer
from scoring.domain.model.valueobjects.shap_factor import ShapFactor


class ShapExplainer(Explainer):
    def __init__(self, booster: xgb.Booster, feature_names: list[str]) -> None:
        self._explainer = shap.TreeExplainer(booster)
        self._feature_names = feature_names

    async def top_factors(self, context, top_n: int = 3) -> list[ShapFactor]:
        features = _vectorize(context)
        shap_values = self._explainer.shap_values([features])[0]
        pairs = sorted(
            zip(self._feature_names, shap_values),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:top_n]
        return [
            ShapFactor(
                feature=name,
                shap_value=float(value),
                direction="increase" if value > 0 else "decrease",
            )
            for name, value in pairs
        ]
```

El servicio guarda los `top-3` factores por `risk_assessment` en la tabla `shap_factors`.

## 8. Combinación en `application`

La combinación la hace el command service (o un `scoring_policy` del dominio). Yo le entrego las piezas:

```python
# application/internal/commandservices/assessment_command_service_impl.py (fragmento)
rules_score   = await self._rule_engine.evaluate(context)      # 0..100
p_xgb         = await self._xgb_model.score(context)           # 0..1
a_iso         = await self._iso_model.score(context)           # 0..1

score = int(round(
    self._weights.rules * rules_score
    + self._weights.xgb * 100 * p_xgb
    + self._weights.iso * 100 * a_iso
))

level = _bucket(score)         # LOW/MEDIUM/HIGH/CRITICAL
factors = await self._explainer.top_factors(context)
```

Umbrales (ADR-007): 0-39 LOW, 40-69 MEDIUM, 70-89 HIGH, 90-100 CRITICAL. Pesos iniciales 0.4 / 0.4 / 0.2.

## 9. Degradación

El servicio arranca y **no debe caerse** si el modelo no carga. En `startup`:

```python
# infrastructure/startup/model_loader.py
import logging

async def load_or_degrade(container) -> None:
    try:
        container.xgb_model = XgboostRiskModel.load(container.settings.xgb_path,
                                                   container.settings.model_version)
        container.iso_model = IsolationForestRiskModel.load(container.settings.iso_path)
        container.explainer = ShapExplainer(container.xgb_model.booster,
                                            container.feature_names)
        container.degraded = False
    except Exception as e:
        logging.getLogger(__name__).error("model-load-failed", extra={"error": str(e)})
        container.xgb_model = None
        container.iso_model = None
        container.explainer = None
        container.degraded = True
```

En el command service, si `self._xgb_model is None`: `p_xgb = 0.0`, `a_iso = 0.0`, se marca `degraded_mode=true` en `risk_assessments`, y no se calcula SHAP (se guardan solo reglas activadas).

## 10. Entrenamiento reproducible

```python
# scripts/train_xgboost.py
"""
Uso: poetry run python scripts/train_xgboost.py \
         --data data/processed/transactions.parquet \
         --out data/models/xgb/
Produce: model.json + metadata.json (version, metrics, features)
"""
import argparse
import json
import uuid
from pathlib import Path

import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score, precision_score, recall_score
from sklearn.model_selection import TimeSeriesSplit


def main(args) -> None:
    df = pd.read_parquet(args.data)
    X = df.drop(columns=["label", "occurred_at"])
    y = df["label"]
    pos_weight = (y == 0).sum() / max((y == 1).sum(), 1)

    splits = TimeSeriesSplit(n_splits=5).split(X)
    *_, (train_idx, test_idx) = splits
    X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
    y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]

    booster = xgb.train(
        params={
            "objective": "binary:logistic",
            "eval_metric": "aucpr",
            "scale_pos_weight": pos_weight,
            "max_depth": 6,
            "eta": 0.1,
            "seed": 42,
        },
        dtrain=xgb.DMatrix(X_tr, label=y_tr),
        num_boost_round=200,
        evals=[(xgb.DMatrix(X_te, label=y_te), "val")],
        early_stopping_rounds=20,
        verbose_eval=False,
    )

    proba = booster.predict(xgb.DMatrix(X_te))
    pred = (proba >= 0.5).astype(int)
    metrics = {
        "pr_auc": float(average_precision_score(y_te, proba)),
        "precision": float(precision_score(y_te, pred, zero_division=0)),
        "recall": float(recall_score(y_te, pred, zero_division=0)),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    version = uuid.uuid4().hex[:12]
    booster.save_model(str(out / f"xgb-{version}.json"))
    (out / f"xgb-{version}.metadata.json").write_text(
        json.dumps({
            "version": version,
            "algorithm": "xgboost",
            "features": list(X.columns),
            "metrics": metrics,
        }, indent=2),
        encoding="utf-8",
    )
    print(f"Saved model version {version} with PR-AUC {metrics['pr_auc']:.3f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--out", required=True)
    main(p.parse_args())
```

El script es **reproducible con `seed=42`**. El `version` se guarda en `model_registry` cuando el servicio lo carga; `is_active=true` en una sola fila.

## 11. Features (compartidas training ↔ runtime)

Para que no haya discrepancia training/serving, la función `_vectorize(context)` vive en **un solo lugar**:

```python
# src/scoring/infrastructure/ml/features.py
from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureVector:
    amount_log: float
    amount_ratio_vs_avg: float
    tx_count_last_5m: int
    new_device: int
    hour_of_day: int
    distance_last_tx_km: float


def vectorize(context) -> list[float]:
    ...
```

Y lo importo igual desde `scripts/train_xgboost.py`. Un cambio en features **obliga** a reentrenar y a versionar.

## 12. Puerta de calidad en CI

```yaml
# .github/workflows/ci.yml (fragmento)
- name: Model quality gate
  run: |
    poetry run python scripts/evaluate_model.py \
      --data data/validation.parquet \
      --model-registry data/models/xgb/
    # El script falla con exit 1 si recall < 0.75 o PR-AUC < 0.60
```

El script `scripts/evaluate_model.py` compara contra la línea base de solo reglas; ambas métricas se registran en el PR.

## 13. Qué **no** hago

- No importo `xgboost` ni `shap` en `domain/`.
- No decido el puntaje final yo solo: la combinación vive en `application`/`domain`.
- No guardo datos sensibles del dataset en el repo.
- No reentreno dentro del servicio en ejecución; eso va aparte, con el script.
- No "mejoro" el modelo sin medir contra PR-AUC y sin que el CI lo acepte.
- No olvido la degradación: siempre hay path "solo reglas".

## 14. Checklist

- [ ] Adaptadores en `infrastructure/ml/` cumpliendo puertos `RiskModel` y `Explainer`.
- [ ] `YamlRuleCatalog` carga `rules.yaml` y cachea.
- [ ] `startup/model_loader.py` soporta degradación sin romper el arranque.
- [ ] `scripts/train_xgboost.py` reproducible con `seed`.
- [ ] `_vectorize(context)` vive en un solo lugar y lo usan training y runtime.
- [ ] Nueva versión → fila en `model_registry` con `is_active`, `metrics`, `trained_at`.
- [ ] SHAP guarda top-3 por assessment en `shap_factors`.
- [ ] Puerta de calidad en CI contra PR-AUC y recall.
- [ ] `data/` está en `.gitignore`.

## 15. Delegación

- Cambio en la forma del puntaje (combinación, umbrales) → **agente `domain`** si es ley de negocio, si no **`application`**.
- Cambio en el esquema de `model_registry` o `shap_factors` → **agente `infrastructure`** (migración Alembic).
- Nuevo campo en el evento `TransactionScoredV1` → **agente `events`**.
- Pruebas (consumer idempotente, degradación, roundtrip de features) → **agente `tests`**.
