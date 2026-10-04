from backend.app.services.core import FleetService
def test_summary(): assert FleetService().fleet_summary()["total_aircraft"]==12
def test_predict(): assert FleetService().predict("AF-003","ENGINE",{"egt_c":790,"vibration_g":.9,"oil_pressure_kpa":290})["alert_level"] in {"SAFE","WARNING","CRITICAL"}
def test_whatif():
 x=FleetService().what_if("AF-003","ENGINE",20); assert x["scenario"]["rul_cycles"]<x["baseline"]["rul_cycles"]
def test_maintenance(): assert "recommended_action" in FleetService().maintenance_recommendation("AF-003",1)