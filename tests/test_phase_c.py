"""Phase C operational hardening tests."""

from ml.observability import PredictionObservability


def test_input_quality_flags_missing_and_invalid_values():
    obs = PredictionObservability()
    result = obs.input_quality({"sensor_1": float("nan")})
    assert result["score"] < 1.0
    assert "sensor_1" in result["invalid_fields"]
    assert "sensor_21" in result["missing_fields"]


def test_explanation_is_transparent_and_non_shap():
    obs = PredictionObservability()
    history = [{"sensor_1": 10.0, "sensor_2": 20.0} for _ in range(5)]
    result = obs.explain(
        {"sensor_1": 12.0, "sensor_2": 20.0},
        history=history,
        failure_probability=.72,
        rul_cycles=30,
        anomaly_score=.75,
    )
    assert result["method"] == "local_signal_attribution"
    assert "SHAP" in " ".join(result["limitations"])
    assert result["decision_reasons"]


def test_audit_metrics_and_drift_contract():
    obs = PredictionObservability()
    telemetry = {"sensor_1": 10.0, "sensor_2": 20.0}
    history = [telemetry.copy(), telemetry.copy(), telemetry.copy()]
    drift = obs.drift("AF-001", "ENGINE", {"sensor_1": 100.0, "sensor_2": 20.0}, history=history, failure_probability=.8, rul_cycles=10)
    assert drift["overall_drift"] is True
    obs.record(
        aircraft_id="AF-001", component="ENGINE", cycle=30,
        telemetry_quality={"score": 1.0},
        prediction={"failure_probability": .8, "rul_cycles": 10, "anomaly_score": .8},
        provenance={"model_version": "TEST"},
        latency_ms=4.2, status="READY", explanation={"method": "test"}, drift=drift,
    )
    metrics = obs.metrics()
    assert metrics["predictions_total"] == 1
    assert metrics["latency_ms"]["p95"] == 4.2
    assert len(obs.audit_records()) == 1


def test_api_exposes_phase_c_observability_contract(tmp_path):
    from fastapi.testclient import TestClient
    import backend.app.main as main_module
    from backend.app.services.core import FleetService
    from digital_twin.state import DigitalTwinStore

    monkeypatch.setattr(main_module, "service", FleetService(twin_store=DigitalTwinStore(tmp_path / "twin.json")))
    client = TestClient(main_module.app)
    response = client.post("/api/predict", json={
        "aircraft_id": "AF-001",
        "component": "ENGINE",
        "telemetry": {"cycle": 1, "sensor_2": 642.0},
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["inference"]["prediction_status"] == "COLD_START"
    assert "provenance" in payload
    assert "observability" in payload
    assert "explanation" in payload["observability"]
    assert "drift" in payload["observability"]

    metrics = client.get("/api/observability")
    assert metrics.status_code == 200
    assert metrics.json()["metrics"]["predictions_total"] >= 1

    audit = client.get("/api/audit?limit=5")
    assert audit.status_code == 200
    assert audit.json()["records"]
    assert audit.json()["records"][-1]["status"] == "COLD_START"
