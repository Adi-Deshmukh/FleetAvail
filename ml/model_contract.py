from dataclasses import dataclass
from typing import Protocol, Any, Mapping

import numpy as np


@dataclass
class Prediction:
    rul_cycles: float
    failure_probability: float
    anomaly_score: float
    confidence: float
    data_quality: float
    model_version: str = "unknown"


class PredictionProvider(Protocol):
    def predict(
        self,
        features: Mapping[str, float],
        sequence: np.ndarray | None = None,
    ) -> Prediction: ...
