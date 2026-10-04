# FleetAvail implementation roadmap

This roadmap follows the completion chain in order. Each layer is independently testable, while the existing synthetic dashboard remains runnable during the transition to trained ML.

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
| 12 | MLOps/explainability | ✅ FD001 provenance, latency/failure metrics, audit trail, local explanations, cold-start/degraded-data semantics, input/output drift and frontend observability |
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

## Phase A — FD001 model-selection milestone

Phase A freezes the project scope at FD001 and makes the existing ML runtime use the validated model benchmark rather than a hard-coded architecture.

Completed:
- Benchmark artifact: models/cmapss/fd001_temporal_rul_comparison.json records baseline, LSTM and TCN test metrics.
- Runtime default is auto.
- auto selects the available RUL branch with the lowest FD001 test MAE.
- Explicit baseline, lstm or tcn selection remains available through FLEETAVAIL_RUL_MODEL.
- If the selected temporal artifact is unavailable, runtime falls back to the baseline and reports the fallback in /api/models.
- /api/models exposes requested model, selected model, selection reason, benchmark comparison and load errors.
- Runtime-selection tests cover best-model selection, temporal-model promotion when it wins, and explicit overrides.

Current FD001 benchmark:
- HistGradientBoosting baseline: MAE 30.83, RMSE 45.10.
- LSTM: MAE 32.45, RMSE 46.29.
- TCN: MAE 33.54, RMSE 47.39.
- Therefore auto selects the baseline.

## Phase B — operational end-to-end milestone

Phase B proves that the existing FD001 components operate as one application workflow rather than as isolated modules.

Completed:
- Public telemetry prediction path validated through FastAPI.
- Prediction output feeds Health Fusion.
- Prediction state is persisted into the Digital Twin.
- Maintenance recommendation consumes the fused aircraft state.
- Maintenance planning consumes fleet/component state and resource constraints.
- Spare allocation consumes the maintenance plan and inventory.
- Fleet availability consumes maintenance and spare feasibility.
- Fleet summary exposes the resulting availability state.
- Added tests/test_phase_b_e2e.py to exercise the full chain through public API contracts.
- Added docs/phase-b.md as the Phase B technical deliverable.

Primary Phase B verification:

    pytest -q tests/test_phase_b_e2e.py

Full suite:

    pytest -q

Phase B remains intentionally limited to FD001. It does not claim production-scale streaming, certified aviation use, real ERP/MRO integration, or model superiority.

## Current architecture boundary

The backend uses the unified C-MAPSS runtime for ENGINE inference when trained artifacts are available. Cold-start handling and fallback behavior keep the demo runnable when a full 30-cycle ML window or artifacts are unavailable.

Non-engine components remain decision-layer/heuristic states because the current trained C-MAPSS models are engine-focused. They must not be represented as if they were trained component-specific models.

## Phase C — operational hardening and MLOps/explainability

Completed:
- Added model/data provenance to engine predictions and audit records.
- Added bounded inference latency and failure metrics.
- Added a 500-record in-process prediction audit buffer and `/api/audit`.
- Added model-agnostic local RUL/failure-risk explanations with explicit limitations.
- Added explicit `COLD_START`, `READY`, `DEGRADED_DATA` and `ERROR` semantics.
- Added telemetry completeness/validity fields and quality scoring.
- Added input drift and rolling prediction-output drift monitoring.
- Added `/api/observability` and frontend observability display.
- Added automated Phase C tests and `docs/phase-c.md`.

Phase C remains intentionally dependency-free at the monitoring layer. It does not claim SHAP attribution, persistent compliance-grade audit storage, Prometheus/OpenTelemetry deployment, population-level drift certification, or aviation safety certification.

## Next implementation target

Phase C is complete. The next target is the final FD001 completion/validation pass and model improvement. Only after FD001 is complete and improved should the pipeline be generalized to FD002, FD003 and FD004.
