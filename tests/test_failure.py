import numpy as np
import pandas as pd

from ml.cmapss.failure import (
    XGBoostFailureRiskModel,
    add_failure_label,
    classification_metrics,
    engine_aware_split,
)


def make_data(engines=12, cycles=40):
    rows = []
    for engine in range(1, engines + 1):
        for cycle in range(1, cycles + 1):
            rul = cycles - cycle
            rows.append({
                "unit_id": engine,
                "cycle": cycle,
                "sensor_a": engine * 0.1 + cycle * 0.02,
                "sensor_b": float(cycle >= cycles - 8),
                "rul": rul,
            })
    return pd.DataFrame(rows)


def test_failure_label_marks_horizon():
    df = pd.DataFrame({"rul": [31, 30, 1, 0]})
    result = add_failure_label(df, horizon=30)
    assert result["failure_within_horizon"].tolist() == [0, 1, 1, 1]


def test_engine_split_never_separates_one_engine():
    df = add_failure_label(make_data(), horizon=10)
    train, calibration, holdout = engine_aware_split(df, random_seed=7)
    groups = [set(frame.unit_id) for frame in (train, calibration, holdout)]
    assert not groups[0] & groups[1]
    assert not groups[0] & groups[2]
    assert not groups[1] & groups[2]
    assert all(
        set(frame.failure_within_horizon) == {0, 1}
        for frame in (train, calibration, holdout)
    )


def test_model_predicts_calibrated_probability_and_round_trips(tmp_path):
    df = add_failure_label(make_data(), horizon=10)
    train, calibration, holdout = engine_aware_split(df, random_seed=7)
    features = ["sensor_a", "sensor_b"]
    model = XGBoostFailureRiskModel.fit(
        train,
        train["failure_within_horizon"],
        calibration,
        calibration["failure_within_horizon"],
        feature_columns=features,
        horizon=10,
        random_seed=7,
    )

    probabilities = model.predict_proba(holdout)
    assert probabilities.shape == (len(holdout),)
    assert np.isfinite(probabilities).all()
    assert ((probabilities >= 0) & (probabilities <= 1)).all()

    metrics = model.evaluate(holdout, holdout["failure_within_horizon"])
    assert metrics["roc_auc"] is not None
    assert metrics["average_precision"] is not None

    path = tmp_path / "failure.joblib"
    model.save(path)
    loaded = XGBoostFailureRiskModel.load(path)
    np.testing.assert_allclose(probabilities, loaded.predict_proba(holdout))


def test_metrics_are_probability_and_threshold_aware():
    result = classification_metrics(
        [0, 0, 1, 1],
        [0.05, 0.2, 0.8, 0.95],
        threshold=0.5,
    )
    assert result["roc_auc"] == 1.0
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["f1"] == 1.0
