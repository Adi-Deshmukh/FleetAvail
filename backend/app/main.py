from pathlib import Path
import asyncio
import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.app.services.core import FleetService

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = ROOT / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"
FRONTEND_SOURCE_INDEX = ROOT / "frontend" / "index.html"
FALLBACK_INDEX = Path(__file__).resolve().parent / "fallback_dashboard.html"
TESTING_INDEX = ROOT / "testing" / "index.html"
service = FleetService()

app = FastAPI(
    title="FleetAvail",
    version="0.2.0",
    description="Aircraft predictive maintenance and fleet availability decision API",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictionRequest(BaseModel):
    aircraft_id: str
    component: str = "ENGINE"
    telemetry: dict[str, float] = Field(default_factory=dict)


class WhatIf(BaseModel):
    aircraft_id: str
    component: str = "ENGINE"
    degradation_pct: float = Field(10, ge=-50, le=200)


class Maintenance(BaseModel):
    aircraft_id: str
    mission_priority: float = Field(1, ge=.1, le=2)


class MaintenanceExecution(BaseModel):
    component: str = "ENGINE"
    action: str = "REPLACE_COMPONENT"
    cycle: int = Field(..., ge=0)


class PlanningOptions(BaseModel):
    mission_priority: float = Field(1, ge=.1, le=2)
    horizon_days: int = Field(7, ge=1, le=30)
    max_daily_hours: float = Field(24, gt=0, le=168)


@app.get("/")
def _dashboard_index() -> Path:
    if FRONTEND_INDEX.exists():
        return FRONTEND_INDEX
    if FALLBACK_INDEX.exists():
        return FALLBACK_INDEX
    # Keep a hard failure explicit rather than returning a blank page.
    raise RuntimeError("FleetAvail dashboard assets are missing")

@app.get("/")
def root():
    return FileResponse(_dashboard_index())

@app.get("/fleetavail/testing")
@app.get("/fleetavail/testing/")
def testing_report():
    if not TESTING_INDEX.exists():
        raise HTTPException(status_code=404, detail="Testing report not found")
    return FileResponse(TESTING_INDEX)

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")


@app.get("/health")
def health():
    return service.health()


@app.get("/api/models")
def models():
    return service.runtime.model_status


@app.get("/api/observability")
def observability():
    return service.observability_status()


@app.get("/api/audit")
def audit(limit: int = 50):
    return {
        "count": min(max(limit, 1), 500),
        "records": service.observability.audit_records(limit),
    }


@app.get("/api/fleet/summary")
def summary():
    return service.fleet_summary()


@app.get("/api/fleet/availability")
def fleet_availability():
    return service.fleet_availability()


@app.get("/api/fleet/aircraft")
def aircraft():
    return service.aircraft_list()


@app.get("/api/fleet/aircraft/{aircraft_id}")
def detail(aircraft_id: str):
    try:
        return service.aircraft_detail(aircraft_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Aircraft not found")


@app.get("/api/fleet/aircraft/{aircraft_id}/twin")
def twin(aircraft_id: str):
    try:
        return service.twin_snapshot(aircraft_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Aircraft not found")


@app.post("/api/fleet/aircraft/{aircraft_id}/maintenance")
def execute_maintenance(aircraft_id: str, x: MaintenanceExecution):
    try:
        return service.record_maintenance(
            aircraft_id,
            x.component.upper(),
            x.action,
            x.cycle,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/predict")
def predict(x: PredictionRequest):
    if x.aircraft_id not in service.aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    try:
        return service.predict(x.aircraft_id, x.component.upper(), x.telemetry)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/simulate/what-if")
def whatif(x: WhatIf):
    try:
        return service.what_if(
            x.aircraft_id,
            x.component.upper(),
            x.degradation_pct,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Aircraft not found")


@app.post("/api/maintenance/recommend")
def recommend(x: Maintenance):
    try:
        return service.maintenance_recommendation(
            x.aircraft_id,
            x.mission_priority,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Aircraft not found")


@app.post("/api/maintenance/plan")
def maintenance_plan(x: PlanningOptions):
    return service.maintenance_plan(
        mission_priority=x.mission_priority,
        horizon_days=x.horizon_days,
        max_daily_hours=x.max_daily_hours,
    )


@app.get("/api/spares")
def spares():
    return service.spares()


@app.post("/api/spares/allocate")
def allocate_spares(x: PlanningOptions):
    return service.allocate_spares_for_plan(
        mission_priority=x.mission_priority,
        horizon_days=x.horizon_days,
        max_daily_hours=x.max_daily_hours,
    )


@app.post("/api/fleet/availability")
def projected_availability(x: PlanningOptions):
    return service.fleet_availability(
        mission_priority=x.mission_priority,
        horizon_days=x.horizon_days,
        max_daily_hours=x.max_daily_hours,
    )


@app.websocket("/ws/telemetry")
async def ws(socket: WebSocket):
    aircraft_id = socket.query_params.get("aircraft_id", "AF-001").upper()
    if aircraft_id not in service.aircraft:
        await socket.close(code=1008, reason="Unknown aircraft")
        return
    await socket.accept()
    try:
        while True:
            await socket.send_text(json.dumps(service.next_telemetry_event(aircraft_id)))
            await asyncio.sleep(1)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass

@app.get("/{path:path}")
def spa_fallback(path: str):
    """Serve the Vite SPA for browser routes while leaving API routes untouched."""
    if path.startswith(("api/", "health", "ws/", "assets/", "docs", "redoc", "openapi.json")):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(_dashboard_index())
