# C-MAPSS implementation

## Dataset
Use the official NASA C-MAPSS turbofan dataset. It is not bundled in Git because the raw files are large and the dataset has its own distribution terms.

Expected layout:
data/raw/cmapss/FD001/train.txt
data/raw/cmapss/FD001/test.txt
data/raw/cmapss/FD001/RUL_test.txt

Repeat for FD002, FD003 and FD004 if those subsets are used.

## Why this pipeline is leakage-safe
- RUL for training is generated from each training unit's maximum observed cycle.
- Test RUL uses only the official RUL_test.txt terminal-life values.
- Scaling is fitted on training data only.
- Temporal features are calculated independently inside each engine/unit.
- Sequence windows never cross engine boundaries.
- Test metrics are calculated on held-out test units, not random rows.
- The model target is capped at 125 cycles for training, a common practical C-MAPSS convention.

## Current model
The first provider is a CPU-friendly HistGradientBoostingRegressor over sequence summaries: last state, mean, standard deviation and start-to-end delta. This is deliberate: it makes the complete pipeline reproducible on a student laptop.

It is a baseline, not the final research model. The next upgrade is a true temporal LSTM/TCN/Transformer provider using the same PredictionProvider contract.

## Train

python scripts/train_cmapss.py --subset FD001 --window 30

This writes:
models/cmapss/fd001_rul.joblib
models/cmapss/fd001_rul.json

## Predict terminal RUL

python scripts/predict_cmapss.py --subset FD001

## Recommended experiment order
1. FD001 baseline.
2. Compare windows 20, 30, 50.
3. Add causal rolling features.
4. Add XGBoost baseline.
5. Add LSTM/TCN.
6. Calibrate uncertainty.
7. Evaluate cross-subset generalisation.


## XGBoost failure-risk model

The failure-risk branch is trained independently from the existing RUL baseline. A row is labeled as failure-risk when its RUL is less than or equal to a configurable horizon; the default is 30 cycles.

The implementation is in:
- `ml/cmapss/failure_risk.py`
- `scripts/train_failure.py`
- `scripts/predict_failure.py`
- `tests/test_failure.py`

The training workflow is engine-aware: complete engine trajectories are split into training, calibration and holdout groups, so rows from the same engine cannot leak across those sets. XGBoost is trained on the leakage-safe temporal features, class imbalance is handled with `scale_pos_weight`, and a sigmoid/Platt calibrator is fit only on the held-out calibration engines.

Train:

```powershell
python scripts/train_failure.py --subset FD001 --horizon 30
```

This writes:

```
models/cmapss/fd001_failure.joblib
models/cmapss/fd001_failure.json
```

Evaluate and print terminal-engine failure-risk predictions:

```powershell
python scripts/predict_failure.py --subset FD001
```

Focused tests:

```powershell
pytest -q tests/test_failure.py
```

The XGBoost branch is currently a standalone validated modeling feature. FastAPI integration, Health Fusion and the anomaly branch are later stages and are not changed by this feature.
