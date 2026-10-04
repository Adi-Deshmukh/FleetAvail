from dataclasses import dataclass
from typing import Protocol
@dataclass
class Prediction:
    rul_cycles: float
    failure_probability: float
    anomaly_score: float
    confidence: float
    data_quality: float
class PredictionProvider(Protocol):
    def predict(self, features: dict[str,float]) -> Prediction: ...
