"""Model-provider adapters used by the FleetAvail inference layer.

The provider contract is intentionally small so the API can evolve from the
current synthetic fallback to trained C-MAPSS/XGBoost/LSTM/TCN/Isolation
Forest artifacts without changing the decision-layer API.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from ml.health import fuse_health
from ml.model_contract import Prediction


@dataclass
class CMapssRULProvider:
    """Wrap a trained C-MAPSS RUL model for terminal-sequence inference."""

    model: Any

    @classmethod
    def load(cls, path: str | Path) -> "CMapssRULProvider":
        from .model import CMapssRULModel

        return cls(CMapssRULModel.load(path))

    @property
    def model_version(self) -> str:
        return self.model.__class__.__name__

    def predict_sequence(self, sequence: np.ndarray) -> float:
        """Predict RUL from one preprocessed [window, features] sequence."""
        batch = np.asarray(sequence, dtype=np.float32)
        if batch.ndim != 2:
            raise ValueError("sequence must have shape [window, features]")
        prediction = self.model.predict(batch[None, ...])
        return float(max(0.0, prediction[0]))


@dataclass
class FusedPredictionProvider:
    """Optional real-RUL provider with a safe heuristic fallback.

    Failure/anomaly branches are deliberately optional for this first slice.
    Later branches can be injected here without changing the API contract.
    """

    rul_provider: CMapssRULProvider | None = None
    fallback_rul: float = 100.0
    model_version: str = "heuristic-v1"

    def predict(
        self,
        features: Mapping[str, float],
        sequence: np.ndarray | None = None,
    ) -> Prediction:
        anomaly = float(np.clip(features.get("anomaly_score", 0.0), 0.0, 1.0))
        risk = float(np.clip(features.get("failure_probability", 0.05), 0.0, 1.0))
        health = float(np.clip(features.get("health", 0.9), 0.0, 1.0))
        data_quality = float(np.clip(features.get("data_quality", 1.0), 0.0, 1.0))

        rul = self.fallback_rul
        version = self.model_version
        if self.rul_provider is not None and sequence is not None:
            rul = self.rul_provider.predict_sequence(sequence)
            version = self.rul_provider.model_version

        fused = fuse_health(health, anomaly, data_quality, risk, rul)
        confidence = float(np.clip(
            0.5 * data_quality + 0.3 * (1.0 - anomaly) + 0.2 * (1.0 - risk),
            0.0,
            1.0,
        ))
        return Prediction(
            rul_cycles=fused["rul_cycles"],
            failure_probability=fused["failure_probability"],
            anomaly_score=fused["anomaly_score"],
            confidence=confidence,
            data_quality=fused["data_quality"],
        )
