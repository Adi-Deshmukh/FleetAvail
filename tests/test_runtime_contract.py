from ml.cmapss.runtime import CMapssModelRuntime


def test_runtime_normalizes_legacy_engine_fields(tmp_path):
    runtime = CMapssModelRuntime(tmp_path)
    row = runtime.normalize_telemetry(
        {"egt_c": 700, "vibration_g": 0.2, "oil_pressure_kpa": 400},
        cycle=7,
    )
    assert row["cycle"] == 7
    assert row["sensor_2"] == 700
    assert row["sensor_3"] == 0.2
    assert row["sensor_4"] == 400
    assert len([k for k in row if k.startswith("sensor_")]) == 21


def test_runtime_has_cold_start_contract(tmp_path):
    runtime = CMapssModelRuntime(tmp_path)
    result = runtime.predict("AF-001", "ENGINE", {"sensor_2": 700}, cycle=1)
    assert result["window_ready"] is False
    assert result["samples_available"] == 1
    assert result["rul_cycles"] is None
    assert 0 <= result["data_quality"] <= 1


def test_runtime_auto_selection_uses_lowest_test_mae():
    comparison = {
        "baseline": {"mae": 30.83, "rmse": 45.10, "score": 0.68},
        "models": {
            "lstm": {"mae": 32.45, "rmse": 46.29, "score": 1.35},
            "tcn": {"mae": 33.54, "rmse": 47.39, "score": 0.87},
        },
    }
    assert CMapssModelRuntime.select_rul_candidate(comparison) == "baseline"


def test_runtime_auto_selection_can_choose_temporal_model_when_better():
    comparison = {
        "baseline": {"mae": 35.0},
        "models": {
            "lstm": {"mae": 28.0},
            "tcn": {"mae": 31.0},
        },
    }
    assert CMapssModelRuntime.select_rul_candidate(comparison) == "lstm"


def test_runtime_explicit_model_selection_overrides_benchmark():
    comparison = {
        "baseline": {"mae": 30.0},
        "models": {"lstm": {"mae": 20.0}},
    }
    assert CMapssModelRuntime.select_rul_candidate(comparison, requested="baseline") == "baseline"
    assert CMapssModelRuntime.select_rul_candidate(comparison, requested="lstm") == "lstm"
