from pathlib import Path
import asyncio,json
from fastapi import FastAPI,WebSocket,WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from backend.app.services.core import FleetService
ROOT=Path(__file__).resolve().parents[2]; service=FleetService()
app=FastAPI(title="FleetAvail",version="0.1.0",description="SIH26249 aircraft predictive maintenance and fleet availability prototype")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])
class Prediction(BaseModel):
 aircraft_id:str; component:str="ENGINE"; telemetry:dict[str,float]=Field(default_factory=dict)
class WhatIf(BaseModel):
 aircraft_id:str; component:str="ENGINE"; degradation_pct:float=Field(10,ge=-50,le=200)
class Maintenance(BaseModel):
 aircraft_id:str; mission_priority:float=Field(1,ge=.1,le=2)
@app.get("/")
def root(): return FileResponse(ROOT/"frontend"/"index.html")
@app.get("/health")
def health(): return service.health()
@app.get("/api/fleet/summary")
def summary(): return service.fleet_summary()
@app.get("/api/fleet/aircraft")
def aircraft(): return service.aircraft_list()
@app.get("/api/fleet/aircraft/{aircraft_id}")
def detail(aircraft_id:str): return service.aircraft_detail(aircraft_id)
@app.post("/api/predict")
def predict(x:Prediction): return service.predict(x.aircraft_id,x.component,x.telemetry)
@app.post("/api/simulate/what-if")
def whatif(x:WhatIf): return service.what_if(x.aircraft_id,x.component,x.degradation_pct)
@app.post("/api/maintenance/recommend")
def recommend(x:Maintenance): return service.maintenance_recommendation(x.aircraft_id,x.mission_priority)
@app.get("/api/spares")
def spares(): return service.spares()
@app.websocket("/ws/telemetry")
async def ws(socket:WebSocket):
 await socket.accept()
 try:
  while True:
   await socket.send_text(json.dumps(service.next_telemetry_event())); await asyncio.sleep(1)
 except (WebSocketDisconnect,asyncio.CancelledError): pass
