# Phase A — FD001 Runtime Completion

## Objective

Complete the current FD001 ML runtime before expanding FleetAvail to FD002, FD003 and FD004.

Phase A does not require trained artifacts to be committed to GitHub. It establishes the correct runtime contract and validated model-selection behavior.

## Deliverables

### 1. Validated RUL model selection

The temporal training workflow produces:

`models/cmapss/fd001_temporal_rul_comparison.json`

It contains the FD001 test metrics for:

- HistGradientBoosting baseline
- LSTM
- TCN

The runtime now defaults to:

`FLEETAVAIL_RUL_MODEL=auto`

In auto mode, the runtime selects the available model with the lowest test MAE.

For the current benchmark:

| Model | MAE | RMSE |
|---|---:|---:|
| HistGradientBoosting | 30.83 | 45.10 |
| LSTM | 32.45 | 46.29 |
| TCN | 33.54 | 47.39 |

Therefore the current FD001 runtime selection is **HistGradientBoosting**.

### 2. Explicit experiment override

The runtime still supports:

`FLEETAVAIL_RUL_MODEL=baseline`

`FLEETAVAIL_RUL_MODEL=lstm`

`FLEETAVAIL_RUL_MODEL=tcn`

This allows controlled model experiments without changing the default production selection.

### 3. Safe artifact fallback

If auto-selection chooses LSTM or TCN but that selected artifact cannot be loaded, the runtime falls back to the baseline when its artifact is available.

The runtime records this condition as:

`selected_artifact_unavailable_fallback_baseline`

### 4. Backend observability

`GET /api/models` now reports:

- runtime mode
- loaded branches
- requested RUL model
- selected RUL model
- selection reason
- benchmark comparison
- artifact loading errors
- required sequence window

This makes the model actually used by the backend inspectable.

### 5. Tests

The runtime contract now tests:

- current FD001 benchmark selects the baseline
- a temporal model is selected automatically when it has the best MAE
- explicit model selection overrides automatic selection

Existing cold-start and telemetry-normalization tests remain unchanged.

## Current scope

Phase A is intentionally **FD001 only**.

Do not expand to FD002–FD004 until the complete FD001 system is validated end-to-end:

Telemetry → RUL/failure/anomaly → health fusion → digital twin → maintenance → spares → fleet availability → API → dashboard.

## Verification

Run locally from the repository root:

```powershell
pytest -q
python -m uvicorn backend.app.main:app --reload --port 8000
```

Then inspect:

```text
GET /api/models
POST /api/predict
GET /api/fleet/summary
GET /api/fleet/availability
GET /api/fleet/aircraft/AF-001/twin
WS /ws/telemetry
```

## Phase A completion criterion

Phase A is complete when the locally trained FD001 artifacts are present, the backend loads the selected RUL branch plus failure/anomaly branches, and the full API/dashboard path has been exercised with real FD001 telemetry.

Artifact packaging/deployment is intentionally deferred.
