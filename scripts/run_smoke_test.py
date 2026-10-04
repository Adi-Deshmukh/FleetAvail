import json,urllib.request
base="http://127.0.0.1:8000"
for p in ["/health","/api/fleet/summary","/api/fleet/aircraft"]:
 with urllib.request.urlopen(base+p,timeout=5) as r: print(p,"OK",r.status)
req=urllib.request.Request(base+"/api/predict",data=json.dumps({"aircraft_id":"AF-003","component":"ENGINE","telemetry":{"egt_c":790,"vibration_g":.9,"oil_pressure_kpa":290}}).encode(),headers={"Content-Type":"application/json"})
with urllib.request.urlopen(req,timeout=5) as r: print("/api/predict","OK",r.status,r.read().decode()[:300])