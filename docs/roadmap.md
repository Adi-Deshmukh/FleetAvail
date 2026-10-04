# FleetAvail implementation roadmap

This roadmap follows the project completion chain in order. Each stage is
kept independently deployable so the existing synthetic dashboard remains
usable while trained ML branches are added.

| Stage | Feature | What it does | Implementation |
|---|---|---|---|
| 1 | C-MAPSS baseline/provider | Turns a 30-cycle telemetry window into an RUL estimate | Keep the existing leakage-aware pipeline and expose the trained artifact through a provider boundary |
| 2 | Telemetry sequence buffer | Maintains bounded per-aircraft/component history | **Implemented:** `ml/sequence_buffer.py` stores the latest 30 valid samples per aircraft/component, enforces cycle ordering, and exposes chronological NumPy windows. |
| 3 | XGBoost failure model | Predicts near-term failure risk | **Implemented:** `ml/cmapss/failure_risk.py` defines the RUL-horizon label, engine-aware splits, XGBoost classifier, held-out sigmoid calibration, metrics, persistence and inference; `scripts/train_failure.py` and `scripts/predict_failure.py` provide reproducible commands. |
| 4 | Isolation Forest | Detects abnormal operating behavior without complete anomaly labels | **Implemented:** `ml/cmapss/anomaly.py` trains on a normal-operation reference population, calibrates a threshold from normal scores, persists metadata, and remains independent of FastAPI/API integration. |
| 5 | Health Fusion | Converts RUL, risk, anomaly, confidence and data quality into an operational state | **Implemented:** explicit NORMAL/WATCH/DEGRADED/CRITICAL fusion with backward-compatible alert levels. |
| 6 | LSTM/TCN RUL | Learns ordered degradation instead of summary-only windows | **Implemented:** LSTM + causal dilated TCN sequence models share the existing 30-cycle C-MAPSS preprocessing, use engine-level train/validation separation, persist scalers, and report MAE/RMSE/score against the HistGradientBoosting baseline. Models remain offline and are not wired to FastAPI. |
| 7 | Real-time ML inference | Runs all trained branches on incoming telemetry | **Implemented:** unified 30-cycle runtime, cold-start handling, local artifact discovery, FastAPI `/api/predict`, `/api/models`, and WebSocket telemetry integration. |
| 8 | Digital twin persistence | Stores component state and maintenance lifecycle | PostgreSQL/Redis-backed aircraft, component, inspection, replacement and degradation state |
| 9 | Maintenance optimizer | Selects maintenance timing/actions under constraints | Start with weighted priority; move to formal OR-Tools optimization |
| 10 | Spare allocation | Allocates constrained compatible inventory across aircraft | Optimize aircraft priority, delay safety and fleet impact |
| 11 | Fleet availability | Quantifies readiness before/after decisions | Model operational/maintenance/spare-blocked states and projected availability |
| 12 | MLOps/explainability | Makes model behavior auditable | Versioning, drift, uncertainty, SHAP, prediction monitoring and recommendation audit trail |
| 13 | Final frontend | Presents the complete decision system | Replace the static dashboard with React/Next.js + Three.js twin, fleet ranking, explanations, spares and what-if controls |

## Current baseline

The repository already contains the C-MAPSS FD001–FD004 loading, leakage-aware
preprocessing, temporal features, 30-cycle sequences and a
HistGradientBoosting RUL baseline. The multi-model architecture is the target,
not a claim that XGBoost/LSTM/TCN/Isolation Forest are already trained.

## Immediate implementation order

1. Keep the current C-MAPSS pipeline reproducible. ✅
2. Add the provider boundary and sequence-aware API contract. ✅
3. Add the 30-cycle telemetry sequence buffer. ✅
4. Add XGBoost failure-risk branch. ✅
5. Add Isolation Forest as an independent branch. ✅
6. Fuse the model outputs. **Implemented:** Health Fusion now produces NORMAL/WATCH/DEGRADED/CRITICAL states.
7. Compare LSTM/TCN with the baseline before replacing the RUL branch. **Implemented:** comparison metadata is emitted by `scripts/train_temporal_rul.py`; replacement is intentionally not automatic.
8. Run real-time inference across the model branches. **Implemented:** FastAPI and WebSocket now consume the unified runtime with cold-start fallback.
9. Persist the twin and then optimize maintenance/spares at fleet level.
10. Upgrade the UI once the backend outputs are stable.


## Feature 2 verification

Run the focused buffer tests:

```powershell
pytest -q tests/test_sequence_buffer.py
```

This verifies the fixed-size rolling window, aircraft/component isolation, chronological feature ordering, duplicate/out-of-order rejection, finite numeric inputs, and incomplete-window behavior.


## Feature 3 verification

XGBoost failure risk is implemented but is not yet connected to the FastAPI runtime. It is trained separately so model validation remains reproducible before API integration.

Install dependencies and run the focused tests:

```powershell
pytest -q tests/test_failure.py
```

Train on FD001 after placing the NASA files under `data/raw/cmapss/FD001/`:

```powershell
python scripts/train_failure.py --subset FD001 --horizon 30
python scripts/predict_failure.py --subset FD001
```

The training command writes `models/cmapss/fd001_failure.joblib` and `models/cmapss/fd001_failure.json`.
\n\n## Feature 6 verification\n\nThe LSTM/TCN branch is intentionally separate from API integration. It reuses the existing C-MAPSS cleaning, constant-feature removal, temporal features, scaling and 30-cycle sequence contract.\n\nTrain both temporal models on FD001:\n\n```powershell\npython scripts/train_temporal_rul.py --subset FD001 --architecture both\n```\n\nThis writes model, metadata, scaler, and comparison artifacts under models/cmapss/. The comparison file includes the existing fd001_rul.json HistGradientBoosting metrics when that baseline metadata is present. Do not replace the baseline unless a temporal model improves the required metrics on the held-out C-MAPSS test set.\n\nRun focused tests:\n\n```powershell\npytest -q tests/test_temporal_rul.py\n```\n\nRun temporal inference after training:\n\n```powershell\npython scripts/predict_temporal_rul.py --subset FD001 --architecture lstm\npython scripts/predict_temporal_rul.py --subset FD001 --architecture tcn\n```\n