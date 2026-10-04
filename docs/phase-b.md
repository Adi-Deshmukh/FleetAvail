# FleetAvail — Phase B Deliverable

## 1. Objective

Phase B completes the operational FD001 decision flow and proves that the current FleetAvail architecture can carry an aircraft state from telemetry through predictive inference and into fleet-level maintenance decisions.

The validated flow is:

```
Telemetry
   ↓
C-MAPSS ML Runtime
   ├── RUL
   ├── Failure Risk
   └── Anomaly
   ↓
Health Fusion
   ↓
Digital Twin
   ↓
Maintenance Recommendation
   ↓
Maintenance Plan
   ↓
Spare Allocation
   ↓
Fleet Availability
   ↓
FastAPI
   ↓
Dashboard / WebSocket consumers
```

Phase B does **not** expand to FD002–FD004 yet. FD001 remains the reference operational dataset.

---

## 2. What Was Delivered

### End-to-end integration test

Added:

`tests/test_phase_b_e2e.py`

The test exercises the public API in business order:

1. Service/model health
2. Model status
3. Engine telemetry submission
4. ML prediction
5. Digital Twin persistence
6. Maintenance recommendation
7. 7-day maintenance planning
8. Spare allocation
9. Fleet availability projection
10. Fleet summary consistency

The test uses the same FastAPI surface consumed by the frontend instead of directly calling internal implementation functions.

### Existing decision-layer APIs validated

The Phase B path covers:

- `GET /health`
- `GET /api/models`
- `POST /api/predict`
- `GET /api/fleet/aircraft/{aircraft_id}/twin`
- `POST /api/maintenance/recommend`
- `POST /api/maintenance/plan`
- `POST /api/spares/allocate`
- `POST /api/fleet/availability`
- `GET /api/fleet/summary`

---

## 3. Input Contract

The engine prediction path accepts the complete C-MAPSS observation:

- 3 operating settings:
  - `op_setting_1`
  - `op_setting_2`
  - `op_setting_3`
- 21 sensors:
  - `sensor_1` … `sensor_21`
- `cycle`

Legacy telemetry aliases are also supported by the runtime:

- `egt_c`
- `vibration_g`
- `oil_pressure_kpa`

The runtime maintains a bounded sequence history and uses a 30-cycle window for sequence-based inference.

---

## 4. Prediction Output

The prediction response contains the fused aircraft/component state plus the underlying inference result.

Core decision signals:

- `health_score`
- `health_level`
- `failure_probability`
- `anomaly_score`
- `rul_cycles`
- `confidence`
- `data_quality`

The inference metadata also exposes:

- model mode
- model version
- selected RUL model
- window readiness

This keeps model output and operational decision state observable.

---

## 5. Digital Twin Integration

Every successful prediction is synchronized into the aircraft's digital twin.

For the tested aircraft:

```
AF-003
  └── ENGINE
       ├── health
       ├── RUL
       ├── failure probability
       ├── anomaly score
       ├── confidence
       ├── data quality
       └── last update cycle
```

The twin also records a `PREDICTION_UPDATE` event.

This establishes the required state transition:

```
Telemetry → Prediction → Persistent Twin State
```

---

## 6. Maintenance Decision Flow

The maintenance optimizer evaluates all aircraft/components using:

- failure probability
- RUL
- mission priority
- maintenance duration
- spare availability
- component-specific spare requirements

The resulting plan is constrained by:

- planning horizon
- maximum daily maintenance hours
- available inventory

The default Phase B validation uses:

- mission priority = `1.0`
- horizon = `7 days`
- daily maintenance capacity = `24 hours`

There are 12 aircraft and 4 tracked components, giving:

```
12 × 4 = 48
```

candidate aircraft/component planning rows before action filtering.

---

## 7. Spare Allocation

Current inventory:

| Part | Quantity | Lead Time |
|---|---:|---:|
| ENG-FLT | 9 | 2 days |
| HYD-PMP | 4 | 6 days |
| ELEC-REG | 6 | 4 days |
| LG-ACT | 3 | 8 days |

The allocator converts planned maintenance into spare requests and prioritizes requests using operational urgency.

The resulting API exposes:

- requests
- allocations
- allocated quantity
- unmet quantity
- allocation rank
- reason
- remaining inventory
- total unmet demand

This is the bridge between predictive maintenance and actual resource feasibility.

---

## 8. Fleet Availability

Fleet availability is calculated after maintenance planning and spare allocation.

The availability layer receives, per aircraft:

- current aircraft status
- maintenance day
- maintenance duration
- spare availability
- criticality

It then calculates:

- current fleet availability
- projected availability
- maintenance impact
- spare-constrained effects

The Phase B test validates that both current and projected availability remain bounded between 0% and 100%.

---

## 9. Operational Data Flow

The complete runtime flow is now:

```
C-MAPSS / live telemetry
        │
        ▼
PredictionRequest
        │
        ▼
FleetService.predict()
        │
        ├───────────────┐
        ▼               ▼
CMapssModelRuntime   telemetry state
        │
        ├── RUL
        ├── failure risk
        └── anomaly
        │
        ▼
Health Fusion
        │
        ▼
DigitalTwinStore
        │
        ▼
Maintenance Optimizer
        │
        ▼
Spare Allocator
        │
        ▼
Fleet Availability Engine
        │
        ▼
FastAPI responses
        │
        ▼
Frontend / operational dashboard
```

---

## 10. Why Phase B Matters

Phase A established that RUL model selection is benchmark-aware.

Phase B establishes that the selected model is not isolated from the rest of the application.

The system now has a validated conceptual path from:

**sensor data → ML prediction → asset state → maintenance decision → spare constraint → fleet availability.**

This is the core product behavior of FleetAvail.

---

## 11. Scope Boundary

Phase B intentionally does not claim:

- production deployment
- certified aviation maintenance decisions
- real airline maintenance-system integration
- real inventory/ERP integration
- real-time streaming at production scale
- validation on FD002, FD003, or FD004
- final model superiority over the current baseline

The current ML benchmark remains:

| Model | MAE | RMSE |
|---|---:|---:|
| Baseline | 30.83 | 45.10 |
| LSTM | 32.45 | 46.29 |
| TCN | 33.54 | 47.39 |

Therefore the runtime's automatic RUL selection currently resolves to the baseline model.

---

## 12. Verification

Run:

```bash
pytest -q tests/test_phase_b_e2e.py
```

Then run the complete suite:

```bash
pytest -q
```

For local model-backed validation, ensure the FD001 data and model artifacts are available under the configured model/data paths.

The GitHub repository does not need to contain the large trained artifacts at this stage.

---

## 13. Phase B Completion Criteria

Phase B is considered implemented when:

- [x] Public prediction API accepts C-MAPSS telemetry
- [x] ML runtime produces the inference contract when artifacts are available
- [x] Health Fusion consumes prediction signals
- [x] Digital Twin receives prediction updates
- [x] Maintenance recommendation consumes aircraft state
- [x] Maintenance planning consumes fleet/component state
- [x] Spare allocation consumes the maintenance plan
- [x] Fleet availability consumes maintenance + spare feasibility
- [x] Fleet summary exposes the resulting availability
- [x] A single integration test exercises the complete chain
- [x] FD001 remains the controlled scope

---

## 14. Next Milestone

The next milestone should **not** immediately add FD002–FD004.

Recommended sequence:

### Phase C — Operational hardening and MLOps

1. Add model/data provenance to every prediction.
2. Add structured inference latency and failure metrics.
3. Add prediction audit records.
4. Add explainability for failure risk and RUL.
5. Add explicit cold-start and degraded-data behavior to the API contract.
6. Add monitoring for drift/data-quality degradation.
7. Strengthen frontend model/decision observability.

After Phase C and final FD001 validation:

### Phase D — Generalize the pipeline

Expand the same runtime contract to:

- FD002
- FD003
- FD004

without duplicating the application architecture.

The intended design is:

```
Dataset
  ↓
Dataset-specific preprocessing
  ↓
Common feature contract
  ↓
Common model/runtime interface
  ↓
Common decision engine
  ↓
Common fleet application
```

This keeps FleetAvail as one system rather than four separate dataset implementations.
