# data/

Carpeta ignorada por git (ver `.gitignore` de la raíz). Aquí se generan los artefactos de training y los modelos serializados:

```
data/
├── raw/              # datasets (synthetic.csv, validation.csv, …)
└── models/
    ├── xgb/          # xgb-<version>.json + xgb-<version>.metadata.json
    └── iforest/      # iforest-<version>.joblib + iforest-<version>.metadata.json
```

Reproducible con los scripts de `scripts/`:

```bash
poetry run python scripts/generate_synthetic_dataset.py --out data/raw/synthetic.csv --rows 20000 --seed 42
poetry run python scripts/train_xgboost.py --data data/raw/synthetic.csv --out data/models/xgb/
poetry run python scripts/train_isolation_forest.py --data data/raw/synthetic.csv --out data/models/iforest/
poetry run python scripts/evaluate_model.py --model data/models/xgb/xgb-<ver>.json --data data/raw/synthetic.csv --pr-auc-min 0.60 --recall-min 0.75
```
