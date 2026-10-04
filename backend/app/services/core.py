from dataclasses import dataclass,field
from datetime import datetime,timezone
import random
COMPONENTS=("ENGINE","HYDRAULIC","ELECTRICAL","LANDING_GEAR")
@dataclass
class Aircraft:
 id:str; status:str; components:dict[str,dict]=field(default_factory=dict)
class FleetService:
 def __init__(self):
  self.rng=random.Random(26249); self.spares_data=[{"part_id":"ENG-FLT","quantity":9,"lead_time_days":2},{"part_id":"HYD-PMP","quantity":4,"lead_time_days":6},{"part_id":"ELEC-REG","quantity":6,"lead_time_days":4},{"part_id":"LG-ACT","quantity":3,"lead_time_days":8}]; self.aircraft={}
  for i in range(1,13):
   comps={}
   for j,c in enumerate(COMPONENTS):
    h=max(.25,min(.98,.82-.025*((i*(j+2))%7)-(0.23 if c=="ENGINE" and i in {3,7,11} else 0)))
    comps[c]={"health":h,"rul":max(8,180*h-i*2),"risk":max(.01,min(.99,1-h+(0.18 if h<.55 else 0))),"anomaly":1-h,"confidence":.83,"data_quality":.98}
   self.aircraft[f"AF-{i:03d}"]=Aircraft(f"AF-{i:03d}",("READY","READY","READY","DEGRADED","MAINTENANCE")[(i-1)%5],comps)
 def health(self): return {"status":"healthy","service":"FleetAvail","aircraft_count":len(self.aircraft),"mode":"synthetic_demo"}
 def fused(self,a,c):
  x=a.components[c]; score=.5*x["health"]+.25*(1-x["anomaly"])+.25*x["data_quality"]; level="CRITICAL" if x["risk"]>=.85 or x["rul"]<20 else ("WARNING" if x["risk"]>=.6 or x["rul"]<45 else "SAFE")
  return {"aircraft_id":a.id,"component":c,"health_score":round(score*100,1),"rul_cycles":round(x["rul"],1),"failure_probability":round(x["risk"],3),"anomaly_score":round(x["anomaly"],3),"confidence":x["confidence"],"data_quality":x["data_quality"],"alert_level":level}
 def fleet_summary(self):
  total=len(self.aircraft); ready=sum(a.status=="READY" for a in self.aircraft.values()); degraded=sum(a.status=="DEGRADED" for a in self.aircraft.values()); maint=total-ready-degraded; critical=sum(self.fused(a,"ENGINE")["alert_level"]=="CRITICAL" for a in self.aircraft.values()); avail=100*ready/total
  return {"total_aircraft":total,"ready":ready,"degraded":degraded,"maintenance":maint,"critical_aircraft":critical,"current_availability_pct":round(avail,1),"projected_7_day_availability_pct":round(max(0,avail-critical*2.5),1)}
 def aircraft_list(self): return [{"aircraft_id":a.id,"status":a.status,"engine":self.fused(a,"ENGINE")} for a in self.aircraft.values()]
 def aircraft_detail(self,aid):
  a=self.aircraft[aid]; return {"aircraft_id":aid,"status":a.status,"components":{c:self.fused(a,c) for c in COMPONENTS}}
 def predict(self,aid,c,t):
  a=self.aircraft[aid]; x=a.components[c]
  if t:
   penalty=max(0,(t.get("egt_c",650)-720)/600)+max(0,(t.get("vibration_g",.12)-.5)/1.5)+max(0,(330-t.get("oil_pressure_kpa",410))/500) if c=="ENGINE" else 0
   x["health"]=max(.05,min(.99,x["health"]-min(.12,penalty*.05))); x["anomaly"]=1-x["health"]; x["risk"]=max(.01,min(.99,1-x["health"])); x["rul"]=max(3,x["rul"]*(.96 if penalty else 1.005))
  return self.fused(a,c)
 def what_if(self,aid,c,p):
  b=self.fused(self.aircraft[aid],c); h=max(1,b["health_score"]*(1-p/100)); rul=max(1,b["rul_cycles"]*(1-p/100)); risk=min(.99,b["failure_probability"]+p/130); avail=self.fleet_summary()["current_availability_pct"]
  return {"baseline":b,"scenario":{"degradation_pct":p,"health_score":round(h,1),"rul_cycles":round(rul,1),"failure_probability":round(risk,3),"projected_fleet_availability_pct":round(max(0,avail-max(0,p)*.12),1)}}
 def maintenance_recommendation(self,aid,mission):
  a=self.aircraft[aid]; rows=sorted([(self.fused(a,c)["failure_probability"]*.65+(1/(1+self.fused(a,c)["rul_cycles"]))*8,c,self.fused(a,c)) for c in COMPONENTS],reverse=True); _,c,p=rows[0]; part={"ENGINE":"ENG-FLT","HYDRAULIC":"HYD-PMP","ELECTRICAL":"ELEC-REG","LANDING_GEAR":"LG-ACT"}[c]; inv=next(x for x in self.spares_data if x["part_id"]==part); action="SCHEDULE_MAINTENANCE" if p["failure_probability"]>=.6 or p["rul_cycles"]<45 else "CONTINUE_MONITORING"; return {"aircraft_id":aid,"priority_component":c,"recommended_action":action,"rul_cycles":p["rul_cycles"],"failure_probability":p["failure_probability"],"spare":inv,"reason_codes":["FAILURE_RISK","RUL_URGENCY","MISSION_PRIORITY","SPARE_AVAILABILITY"]}
 def spares(self): return self.spares_data
 def next_telemetry_event(self):
  a=self.rng.choice(list(self.aircraft.values())); p=self.fused(a,"ENGINE"); return {"timestamp":datetime.now(timezone.utc).isoformat(),"event":"telemetry_update","aircraft_id":a.id,"component":"ENGINE","health_score":p["health_score"],"rul_cycles":p["rul_cycles"],"failure_probability":p["failure_probability"],"alert_level":p["alert_level"]}
