import numpy as np
import pandas as pd
import pytest

from ml.cmapss.anomaly import (
    IsolationForestAnomalyModel,
    anomaly_metrics,
    choose_threshold,
)


def make_data(n_normal=240, n_anomaly=40, seed=7):
    rng = np.random.default_rng(seed)
    normal = pd.DataFrame(
        {
            "sensor_a": rng.normal(0, 1, n_normal),
            "sensor_b": rng.normal(0, 1, n_normal),
        }
    )
    anomaly = pd.DataFrame(
        {
            "sensor_a": rng.normal(6, 0.4, n_anomaly),
            "sensor_b": rng.normal(6, 0.4, n_anomaly),
        }
    )
    return normal, anomaly


def test_threshold_comes_from_normal_reference_population():
    normal, _ = make_data()
    model = IsolationForestAnomalyModel.fit(
        normal,
        feature_columns=["sensor_a", "sensor_b"],
        false_positive_quantile=0.99,
        random_seed=7,
    )
    scores = model.score_samples(normal)
    assert np.isfinite(scores).all()
    assert model.threshold >= np.quantile(scores, 0.98)


def test_isolation_forest_separates_obvious_anomalies():
    normal, anomaly = make_data()
    model = IsolationForestAnomalyModel.fit(
        normal,
        feature_columns=["sensor_a", "sensor_b"],
        false_positive_quantile=0.95,
        random_seed=7,
    )
    X = pd.concat([normal, anomaly], ignore_index=True)
    y = np.array([0] * len(normal) + [1] * len(anomaly), dtype=np.int8)
    metrics = model.evaluate(X, y)
    assert metrics["recall"] > 0.8
    assert metrics["f1"] > 0.7


def test_model_round_trip(tmp_path):
    normal, _ = make_data()
    model = IsolationForestAnomalyModel.fit(
        normal,
        feature_columns=["sensor_a", "sensor_b"],
        random_seed=7,
    )
    path = tmp_path / "anomaly.joblib"
    model.save(path)
    loaded = IsolationForestAnomalyModel.load(path)
    np.testing.assert_allclose(model.score_samples(normal), loaded.score_samples(normal))


def test_invalid_inputs_fail_fast():
    normal, _ = make_data()
    with pytest.raises(ValueError):
        choose_threshold([], false_positive_quantile=0.99)
    with pytest.raises(ValueError):
        IsolationForestAnomalyModel.fit(
            normal.iloc[:10],
            feature_columns=["sensor_a", "sensor_b"],
        )


def test_metrics_contract():
    metrics = anomaly_metrics([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9], 0.5)
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
