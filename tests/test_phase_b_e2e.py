"""Phase-B operational end-to-end validation.

This test deliberately exercises the same business flow used by the dashboard:
telemetry -> ML prediction -> health fusion -> digital twin -> maintenance
recommendation/plan -> spare allocation -> fleet availability.
"""

import pytest
from fastapi.testclient import TestClient

import backend.app.main as main_module
from backend.app.services.core import FleetService
from digital_twin.state import DigitalTwinStore


@pytest.fixture(autouse=True)
def isolated_service(tmp_path):
    main_module.service = FleetService(
        twin_store=DigitalTwinStore(tmp_path / "digital_twin_state.json")
    )


def test_phase_b_end_to_end_operational_flow():
    # 1. Service/model readiness
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    models = client.get("/api/models")
    assert models.status_code == 200
    model_state = models.json()
    assert model_state["mode"] in {"ml", "synthetic_fallback"}
    assert "rul_selection" in model_state
    assert "selected" in model_state["rul_selection"]

    # 2. Ingest one telemetry observation through the public prediction API.
    prediction = client.post(
        "/api/predict",
        json={
            "aircraft_id": "AF-003",
            "component": "ENGINE",
            "telemetry": {
                "cycle": 42,
                "op_setting_1": 0.0002,
                "op_setting_2": -0.0001,
                "op_setting_3": 0.0003,
                "sensor_1": 518.67,
                "sensor_2": 642.1,
                "sensor_3": 1585.0,
                "sensor_4": 1402.0,
                "sensor_5": 8.6,
                "sensor_6": 21.6,
                "sensor_7": 553.0,
                "sensor_8": 2388.0,
                "sensor_9": 9040.0,
                "sensor_10": 1.3,
                "sensor_11": 47.0,
                "sensor_12": 521.0,
                "sensor_13": 2388.0,
                "sensor_14": 8138.0,
                "sensor_15": 8.4,
                "sensor_16": 0.03,
                "sensor_17": 392.0,
                "sensor_18": 2388.0,
                "sensor_19": 100.0,
                "sensor_20": 39.0,
                "sensor_21": 23.4,
            },
        },
    )
    assert prediction.status_code == 200
    predicted = prediction.json()
    assert predicted["aircraft_id"] == "AF-003"
    assert predicted["component"] == "ENGINE"
    assert "health_score" in predicted
    assert "failure_probability" in predicted
    assert "anomaly_score" in predicted
    assert "rul_cycles" in predicted

    # 3. Prediction must persist into the digital twin.
    twin = client.get("/api/fleet/aircraft/AF-003/twin")
    assert twin.status_code == 200
    twin_state = twin.json()
    assert twin_state["components"]["ENGINE"]["last_update_cycle"] == 42
    assert twin_state["events"][-1]["event_type"] == "PREDICTION_UPDATE"

    # 4. Convert aircraft state into a maintenance decision.
    recommendation = client.post(
        "/api/maintenance/recommend",
        json={"aircraft_id": "AF-003", "mission_priority": 1.0},
    )
    assert recommendation.status_code == 200
    rec = recommendation.json()
    assert rec["aircraft_id"] == "AF-003"
    assert rec["priority_component"] in {
        "ENGINE",
        "HYDRAULIC",
        "ELECTRICAL",
        "LANDING_GEAR",
    }
    assert "recommended_action" in rec
    assert "reason_codes" in rec

    # 5. Build the fleet maintenance plan.
    plan = client.post(
        "/api/maintenance/plan",
        json={
            "mission_priority": 1.0,
            "horizon_days": 7,
            "max_daily_hours": 24,
        },
    )
    assert plan.status_code == 200
    plan_payload = plan.json()
    assert plan_payload["horizon_days"] == 7
    assert plan_payload["items"]
    assert all("aircraft_id" in item for item in plan_payload["items"])

    # 6. Allocate constrained spares against that plan.
    allocation = client.post(
        "/api/spares/allocate",
        json={
            "mission_priority": 1.0,
            "horizon_days": 7,
            "max_daily_hours": 24,
        },
    )
    assert allocation.status_code == 200
    allocation_payload = allocation.json()
    assert "requests" in allocation_payload
    assert "allocations" in allocation_payload
    assert "inventory" in allocation_payload
    assert allocation_payload["inventory"]["total_unmet"] >= 0

    # 7. Convert maintenance + spare feasibility into fleet availability.
    availability = client.post(
        "/api/fleet/availability",
        json={
            "mission_priority": 1.0,
            "horizon_days": 7,
            "max_daily_hours": 24,
        },
    )
    assert availability.status_code == 200
    availability_payload = availability.json()
    assert availability_payload["total_aircraft"] == 12
    assert 0 <= availability_payload["current_availability_pct"] <= 100
    assert 0 <= availability_payload["projected_availability_pct"] <= 100
    assert availability_payload["maintenance_plan_items"] == len(
        plan_payload["items"]
    )
    assert availability_payload["spare_unmet_requests"] >= 0

    # 8. Confirm the fleet summary exposes the same decision-layer result.
    summary = client.get("/api/fleet/summary")
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["total_aircraft"] == 12
    assert 0 <= summary_payload["current_availability_pct"] <= 100


client = TestClient(main_module.app)


def test_fleet_readiness_tracks_engine_health_state():
    aircraft = main_module.service.aircraft["AF-001"]
    aircraft.status = "READY"
    aircraft.components["ENGINE"].update({
        "health": 0.25,
        "risk": 0.92,
        "anomaly": 0.91,
        "rul": 12.0,
    })

    fleet = client.get("/api/fleet/aircraft").json()
    row = next(item for item in fleet if item["aircraft_id"] == "AF-001")
    assert row["status"] == "CRITICAL"
    assert row["engine"]["health_level"] == "CRITICAL"

    summary = client.get("/api/fleet/summary").json()
    assert summary["critical_aircraft"] >= 1
    assert summary["ready"] + summary["degraded"] + summary["maintenance"] + summary["critical_aircraft"] == 12


def test_websocket_telemetry_is_pinned_and_runs_inference():
    with client.websocket_connect("/ws/telemetry?aircraft_id=AF-001") as websocket:
        first = websocket.receive_json()
        second = websocket.receive_json()

    assert first["aircraft_id"] == "AF-001"
    assert second["aircraft_id"] == "AF-001"
    assert first["component"] == "ENGINE"
    assert second["component"] == "ENGINE"
    assert "failure_probability" in first
    assert "anomaly_score" in first
    assert "prediction_status" in first
    assert second["cycle"] >= first["cycle"]


def test_fleet_availability_reports_current_and_projected_blocks():
    availability = client.get("/api/fleet/availability").json()
    assert "current_blocked_aircraft" in availability
    assert "projected_blocked_aircraft" in availability
    assert set(availability["recovered_aircraft"]).isdisjoint(
        set(availability["projected_blocked_aircraft"])
    )


def test_aircraft_detail_mission_status_matches_operational_state():
    aircraft = main_module.service.aircraft["AF-003"]
    aircraft.status = "READY"
    aircraft.components["ENGINE"].update({
        "health": 0.40,
        "risk": 0.74,
        "anomaly": 0.60,
        "rul": 73.0,
    })

    detail = client.get("/api/fleet/aircraft/AF-003").json()
    assert detail["status"] == "DEGRADED"
    assert detail["twin_state"]["mission_status"] == "DEGRADED"
    assert detail["components"]["ENGINE"]["health_level"] == "DEGRADED"
    assert "ELEVATED_FAILURE_RISK" in detail["components"]["ENGINE"]["reason_codes"]
