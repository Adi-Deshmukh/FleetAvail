# FleetAvail

**SIH26249 — Air Power: Predictive Maintenance & Fleet Availability**

FleetAvail is an integration prototype for aircraft health monitoring, predictive maintenance and fleet-level availability decisions.

## Implemented
- Subsystem-oriented aircraft health: engine, hydraulics, electrical, landing gear
- Health fusion: health score, RUL, failure probability, anomaly score, confidence and data quality
- Digital-twin-style aircraft/component state
- What-if degradation simulation
- Maintenance prioritisation with spare-part awareness
- Fleet availability and projected availability
- Synthetic telemetry over WebSocket
- FastAPI REST API
- Runnable command dashboard
- Pytest coverage

The current inference provider is intentionally synthetic/heuristic so the repository runs without proprietary aircraft data or downloaded model weights. It leaves a clean replacement point for C-MAPSS-trained XGBoost/LSTM/TCN models.

## Architecture
Telemetry + maintenance history -> validation/features -> anomaly + failure-risk + RUL -> health fusion -> digital twin -> maintenance/spares -> fleet availability -> dashboard.

## Reference architecture sources
The design was informed by public repository architectures from AeroSentinal, Dattateja's aircraft predictive-maintenance system, DRDO-UAV-EngineTwin, Ocramnaig94's aircraft digital twin, Saroswat's leakage-aware C-MAPSS project, and Karthikeyan's deployable RUL project. This repository is an original integration scaffold; source code/assets are not copied wholesale.

## Setup
See docs/setup.md.

Windows:
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/generate_demo_data.py
python -m uvicorn backend.app.main:app --reload --port 8000

Open http://127.0.0.1:8000/ for the dashboard and http://127.0.0.1:8000/docs for Swagger.

Second terminal:
python scripts/run_smoke_test.py
pytest -q

## API
GET /health
GET /api/fleet/summary
GET /api/fleet/aircraft
GET /api/fleet/aircraft/{aircraft_id}
POST /api/predict
POST /api/simulate/what-if
POST /api/maintenance/recommend
GET /api/spares
WS /ws/telemetry

## Next layer
1. Replace the heuristic provider with leakage-aware C-MAPSS training.
2. Add a temporal RUL model and failure classifier behind the same API contract.
3. Add maintenance-history and component-lifecycle schemas.
4. Add PostgreSQL/Redis persistence.
5. Add React/Next.js + Three.js digital-twin UI.
6. Add uncertainty calibration, SHAP explanations and drift/OOD monitoring.
7. Add OR-Tools maintenance/spares optimisation.

## Limitation
This is a software prototype, not a certified aviation or defence system. Demo telemetry is synthetic and must not be interpreted as real Indian military aircraft data.
