# FleetAvail implementation roadmap

This roadmap follows the completion chain in order. Each layer is independently testable,
while the existing synthetic dashboard remains runnable during the transition to trained ML.

| Stage | Feature | Current implementation |
|---|---|---|
| 1 | C-MAPSS baseline/provider | ✅ Leakage-aware preprocessing, 30-cycle windows, baseline RUL model and provider boundary |
| 2 | Telemetry sequence buffer | ✅ Bounded per-aircraft/component 30-cycle history with ordering validation |
| 3 | XGBoost failure model | ✅ Near-term failure risk with engine-aware splitting and probability calibration |
| 4 | Isolation Forest | ✅ Normal-reference anomaly detector with calibrated threshold and persistence |
| 5 | Health Fusion | ✅ Typed NORMAL/WATCH/DEGRADED/CRITICAL state with reason codes |
| 6 | LSTM/TCN RUL | ✅ LSTM and causal dilated TCN training/inference branch; benchmarked against baseline |
| 7 | Real-time ML inference | ✅ Unified 30-cycle runtime with automatic validated-model selection, model loading, cold-start fallback, FastAPI and WebSocket integration |
| 8 | Digital Twin persistence | ✅ Persistent aircraft/component lifecycle state and event history using atomic local JSON; backend-neutral store API |
| 9 | Maintenance optimizer | ✅ Constraint-aware 7-day scheduling with risk/RUL/mission priority, duration and spare constraints |
| 10 | Spare allocation | ✅ Priority-aware allocation that never exceeds compatible inventory and reports unmet demand |
| 11 | Fleet availability | ✅ Current/projected readiness calculation using maintenance schedules and spare feasibility |
| 12 | MLOps/explainability | ⏳ Versioning, drift, uncertainty, SHAP, prediction monitoring and audit trail |
| 13 | Final frontend | ⏳ React/Next.js + Three.js operational dashboard |

## Current architecture

Telemetry + maintenance history
→ validation / data quality
→ leakage-aware preprocessing
→ XGBoost failure risk + LSTM/TCN RUL + Isolation Forest anomaly
→ Health Fusion
→ Digital Twin
→ Maintenance Optimizer
→ Spare Allocation
→ Fleet Availability
→ API / dashboard

## Important implementation boundary

The repository now contains the decision layers requested in stages 5 and 8–11.
The FastAPI service now uses the unified runtime for ENGINE inference when trained artifacts are available, with cold-start and synthetic fallback keeping the demo runnable.

## Feature 5 — Health Fusion verification

Run:
pytest -q tests/test_health_fusion.py

The tests cover the four operational states, reason codes, legacy compatibility, and invalid inputs.

## Feature 8 — Digital Twin verification

The store persists component predictions, lifecycle status, maintenance events and the latest bounded
event history. It defaults to data/digital_twin_state.json.

Run:
pytest -q tests/test_decision_layers.py -k digital_twin

The persistence file is local runtime state and is ignored by Git.

## Feature 9 — Maintenance optimizer verification

Run:
pytest -q tests/test_decision_layers.py -k maintenance

The planner ranks candidates using failure risk, RUL urgency, mission priority and spare availability,
then respects a daily maintenance-hour capacity.

API:
curl.exe -X POST http://127.0.0.1:8000/api/maintenance/plan -H "Content-Type: application/json" -d "{\"mission_priority\":1,\"horizon_days\":7,\"max_daily_hours\":24}"

## Feature 10 — Spare allocation verification

Run:
pytest -q tests/test_decision_layers.py -k spare

The allocator uses only compatible stock and never allocates more than the available quantity.
The response reports allocated and unmet demand.

API:
curl.exe -X POST http://127.0.0.1:8000/api/spares/allocate -H "Content-Type: application/json" -d "{\"mission_priority\":1,\"horizon_days\":7,\"max_daily_hours\":24}"

## Feature 11 — Fleet availability verification

Run:
pytest -q tests/test_decision_layers.py -k fleet_availability

The calculation reports current readiness, projected readiness, blocked aircraft and aircraft that
can recover within the planning horizon when maintenance and compatible spares are available.

API:
curl.exe http://127.0.0.1:8000/api/fleet/availability

or:
curl.exe -X POST http://127.0.0.1:8000/api/fleet/availability -H "Content-Type: application/json" -d "{\"mission_priority\":1,\"horizon_days\":7,\"max_daily_hours\":24}"

## Full verification

From the repository root:
pip install -r requirements.txt
pytest -q tests/test_health_fusion.py
pytest -q tests/test_decision_layers.py
pytest -q tests/test_api_decision_layers.py
pytest -q
python -m uvicorn backend.app.main:app --reload --port 8000

## C-MAPSS training remains separate

The NASA dataset is not committed. Put these files under data/raw/cmapss/FD001/:
train.txt
test.txt
RUL_test.txt

LSTM/TCN additionally require TensorFlow in the local Python environment because TensorFlow is intentionally
not part of the base requirements file.

## Phase A — FD001 completion milestone

Phase A freezes the project scope at FD001 and makes the existing ML runtime use the validated model benchmark rather than a hard-coded architecture.

Completed:
- Benchmark artifact: `models/cmapss/fd001_temporal_rul_comparison.json` records baseline, LSTM and TCN test metrics.
- Runtime default is `auto`.
- `auto` selects the available RUL branch with the lowest FD001 test MAE.
- Explicit `baseline`, `lstm` or `tcn` selection remains available through `FLEETAVAIL_RUL_MODEL` for controlled experiments.
- If the selected temporal artifact is unavailable, runtime falls back to the baseline and reports the fallback in `/api/models`.
- `/api/models` exposes requested model, selected model, selection reason, benchmark comparison and load errors.
- Runtime-selection tests cover best-model selection, temporal-model promotion when it wins, and explicit overrides.

For the current benchmark:
- HistGradientBoosting baseline: MAE 30.83, RMSE 45.10.
- LSTM: MAE 32.45, RMSE 46.29.
- TCN: MAE 33.54, RMSE 47.39.
- Therefore `auto` selects the baseline for the current FD001 benchmark.

The trained artifacts themselves are intentionally not required to be committed to GitHub in this phase.

## Next implementation target

Finish the remaining FD001 end-to-end validation and operational hardening before expanding to FD002, FD003 and FD004. MLOps/explainability follows that completion pass.
