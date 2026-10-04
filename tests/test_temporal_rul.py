import numpy as np
import pytest

from ml.cmapss.temporal_rul import regression_metrics


def test_regression_metrics_contract():
    y = np.array([10.0, 20.0, 30.0])
    p = np.array([12.0, 18.0, 31.0])
    metrics = regression_metrics(y, p)
    assert set(metrics) == {"mae", "rmse", "score"}
    assert metrics["mae"] >= 0
    assert metrics["rmse"] >= 0
    assert metrics["score"] >= 0


def test_negative_predictions_are_clipped():
    metrics = regression_metrics(np.array([0.0, 5.0]), np.array([-4.0, 5.0]))
    assert metrics["mae"] == pytest.approx(0.0)


def test_model_builders_have_expected_output_shape():
    tf = pytest.importorskip("tensorflow")
    from ml.cmapss.temporal_rul import build_lstm, build_tcn

    for builder in (build_lstm, build_tcn):
        model = builder((30, 10))
        assert model.output_shape == (None, 1)
        assert model.input_shape == (None, 30, 10)
