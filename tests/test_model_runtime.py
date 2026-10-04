from pathlib import Path

from backend.app.services.core import FleetService
from digital_twin.state import DigitalTwinStore
from ml.cmapss.failure_risk import XGBoostFailureRiskModel
from ml.cmapss.anomaly import IsolationForestAnomalyModel
from ml.cmapss.runtime import CMapssModelRuntime


def test_runtime_loads_independent_failure_and_anomaly_branches(tmp_path, monkeypatch):
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    failure_path = model_dir / "fd001_failure.joblib"
    anomaly_path = model_dir / "fd001_isolation_forest.joblib"
    failure_path.touch()
    anomaly_path.touch()

    class StubFailure:
        feature_columns = ["sensor_1"]
        metadata = {"dataset": "FD001"}

        def predict_proba(self, frame):
            return [0.42]

    class StubAnomaly:
        feature_columns = ["sensor_1"]
        threshold = 0.5
        metadata = {"dataset": "FD001"}

        def score_samples(self, frame):
            return [0.7]

    monkeypatch.setattr(XGBoostFailureRiskModel, "load", classmethod(lambda cls, path: StubFailure()))
    monkeypatch.setattr(IsolationForestAnomalyModel, "load", classmethod(lambda cls, path: StubAnomaly()))

    runtime = CMapssModelRuntime(model_dir)

    assert runtime.model_status["production_branches"]["failure"]["status"] == "ACTIVE"
    assert runtime.model_status["production_branches"]["anomaly"]["status"] == "ACTIVE"
    assert runtime.model_status["production_branches"]["failure"]["model"] == "XGBOOST_FAILURE_RISK"
    assert runtime.model_status["production_branches"]["anomaly"]["model"] == "ISOLATION_FOREST_ANOMALY"
    assert runtime.model_status["branches"]["failure"]["loaded"] is True
    assert runtime.model_status["branches"]["anomaly"]["loaded"] is True


def test_runtime_reports_missing_production_artifacts(tmp_path):
    runtime = CMapssModelRuntime(tmp_path)

    status = runtime.model_status["production_branches"]
    assert status["failure"]["status"] == "UNAVAILABLE"
    assert status["anomaly"]["status"] == "UNAVAILABLE"
    assert "Missing artifact" in status["failure"]["error"]
    assert "Missing artifact" in status["anomaly"]["error"]


def test_live_telemetry_signal_is_smoothed_without_changing_model_contract(tmp_path):
    service = FleetService(twin_store=DigitalTwinStore(tmp_path / "twin.json"))
    outputs = iter([
        {
            "health_score": 100.0,
            "rul_cycles": 120.0,
            "failure_probability": 0.10,
            "anomaly_score": 0.10,
            "confidence": 0.9,
            "data_quality": 1.0,
            "health_level": "NORMAL",
        },
        {
            "health_score": 0.0,
            "rul_cycles": 80.0,
            "failure_probability": 0.90,
            "anomaly_score": 0.90,
            "confidence": 0.6,
            "data_quality": 1.0,
            "health_level": "DEGRADED",
        },
    ])

    service.predict = lambda *args, **kwargs: next(outputs)

    first = service.next_telemetry_event("AF-001")
    second = service.next_telemetry_event("AF-001")

    assert first["health_score"] == 100.0
    assert second["health_score"] == 80.0
    assert second["failure_probability"] == 0.26
    assert second["anomaly_score"] == 0.26
    assert "raw_health_score" in second
    assert second["raw_health_score"] == 0.0
