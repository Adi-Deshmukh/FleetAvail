# Phase C — Operational Hardening, MLOps and Explainability

Phase C turns the FD001 inference path into an observable operational service. It does not claim production aviation certification, external telemetry infrastructure, or model superiority.

## Deliverables

1. **Prediction/model provenance** — every engine prediction records FD001 scope, Phase C contract version, runtime mode, requested/selected RUL branch, loaded model branches, artifact paths and window size.
2. **Inference latency and failure metrics** — bounded counters plus last, mean and p95 latency through GET /api/observability.
3. **Prediction audit trail** — latest 500 records through GET /api/audit?limit=N, including outputs, quality, provenance, explanation, drift and errors.
4. **RUL/failure-risk explainability** — transparent local signal attribution using standardized sensor deviations and decision reasons. It is explicitly not SHAP or causal attribution.
5. **Cold-start/degraded-data semantics** — COLD_START, READY, DEGRADED_DATA and ERROR states plus input_quality, missing_fields, invalid_fields, window_ready and samples_available.
6. **Data/model drift monitoring** — input z-score drift and rolling prediction-output shift for failure risk and RUL.
7. **Frontend observability** — runtime mode, selected RUL model, Phase C version and live metrics are displayed in the Command Center.

## Flow

Telemetry → input quality → 30-cycle buffer → cold-start or ML inference → Health Fusion → explanation + drift + provenance + latency → Digital Twin → audit → maintenance/spares/availability → API/dashboard.

## Verification

    pytest -q tests/test_phase_c.py
    pytest -q tests/test_phase_b_e2e.py
    pytest -q
    python -m compileall backend decision_engine digital_twin ml scripts

## Completion matrix

| Deliverable | Status |
|---|---|
| Model/data provenance | Complete |
| Inference latency/failure metrics | Complete |
| Prediction audit records | Complete |
| Local RUL/failure-risk explanation | Complete |
| Cold-start semantics | Complete |
| Degraded-data semantics | Complete |
| Input drift monitoring | Complete |
| Prediction-output drift monitoring | Complete |
| Frontend observability | Complete |
| Automated tests | Complete |
| Documentation | Complete |

## Scope boundary

This is an application-level FD001 prototype. It is not a replacement for persistent compliance-grade audit storage, Prometheus/OpenTelemetry deployment, population-level drift certification, model-specific SHAP adapters, or aviation safety certification.

The next milestone is the final FD001 completion/validation pass and model improvement. FD002–FD004 expansion follows that pass.
