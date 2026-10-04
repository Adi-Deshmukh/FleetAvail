from pathlib import Path
import asyncio
import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.app.services.core import FleetService

ROOT = Path(__file__).resolve().parents[2]
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


@app.get("/")
def root():
    return FileResponse(ROOT / "frontend" / "index.html")


@app.get("/health")
def health():
    return service.health()


@app.get("/api/models")
def models():
    return service.runtime.model_status


@app.get("/api/fleet/summary")
def summary():
    return service.fleet_summary()


@app.get("/api/fleet/aircraft")
def aircraft():
    return service.aircraft_list()


@app.get("/api/fleet/aircraft/{aircraft_id}")
def detail(aircraft_id: str):
    try:
        return service.aircraft_detail(aircraft_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Aircraft not found")


@app.post("/api/predict")
def predict(x: PredictionRequest):
    try:
        return service.predict(x.aircraft_id, x.component.upper(), x.telemetry)
    except KeyError:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/simulate/what-if")
def whatif(x: WhatIf):
    try:
        return service.what_if(x.aircraft_id, x.component.upper(), x.degradation_pct)
    except KeyError:
        raise HTTPException(status_code=404, detail="Aircraft not found")


@app.post("/api/maintenance/recommend")
def recommend(x: Maintenance):
    try:
        return service.maintenance_recommendation(x.aircraft_id, x.mission_priority)
    except KeyError:
        raise HTTPException(status_code=404, detail="Aircraft not found")


@app.get("/api/spares")
def spares():
    return service.spares()


@app.websocket("/ws/telemetry")
async def ws(socket: WebSocket):
    await socket.accept()
    try:
        while True:
            await socket.send_text(json.dumps(service.next_telemetry_event()))
            await asyncio.sleep(1)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
