# FleetAvail implementation roadmap

This roadmap follows the project completion chain in order. Each stage is
kept independently deployable so the existing synthetic dashboard remains
usable while trained ML branches are added.

| Stage | Feature | What it does | Implementation |
|---|---|---|---|
| 1 | C-MAPSS baseline/provider | Turns a 30-cycle telemetry window into an RUL estimate | Keep the existing leakage-aware pipeline and expose the trained artifact through a provider boundary |
| 2 | Telemetry sequence buffer | Maintains bounded per-aircraft/component history | **Implemented:** `ml/sequence_buffer.py` stores the latest 30 valid samples per aircraft/component, enforces cycle ordering, and exposes chronological NumPy windows. |
| 3 | XGBoost failure model | Predicts near-term failure risk | **Implemented:** `ml/cmapss/failure_risk.py` defines the RUL-horizon label, engine-aware splits, XGBoost classifier, held-out sigmoid calibration, metrics, persistence and inference; `scripts/train_failure.py` and `scripts/predict_failure.py` provide reproducible commands. |
| 4 | Isolation Forest | Detects abnormal operating behavior without complete anomaly labels | Train on normal-operation reference data; calibrate threshold and quality/OOD checks |
| 5 | Health Fusion | Converts RUL, risk, anomaly, confidence and data quality into an operational state | Implement a typed HealthState and explicit NORMAL/WATCH/DEGRADED/CRITICAL rules |
| 6 | LSTM/TCN RUL | Learns ordered degradation instead of summary-only windows | Train LSTM baseline, TCN alternative, compare against HistGradientBoosting |
| 7 | Real-time ML inference | Runs all trained branches on incoming telemetry | Wire providers into FastAPI with cold-start fallback and model metadata |
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
5. Add Isolation Forest as an independent branch.
6. Fuse the model outputs.
7. Compare LSTM/TCN with the baseline before replacing the RUL branch.
8. Persist the twin and then optimize maintenance/spares at fleet level.
9. Upgrade the UI once the backend outputs are stable.


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
