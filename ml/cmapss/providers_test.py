import numpy as np

from ml.cmapss.providers import CMapssRULProvider


class StubModel:
    def predict(self, batch):
        assert batch.shape == (1, 30, 2)
        return np.array([37.5], dtype=float)


def test_cmapss_provider_predicts_single_sequence():
    provider = CMapssRULProvider(StubModel())
    result = provider.predict_sequence(np.zeros((30, 2), dtype=np.float32))
    assert result == 37.5
