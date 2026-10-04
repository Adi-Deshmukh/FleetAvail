from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score


def _feature_frame(X: pd.DataFrame, feature_columns: Sequence[str]) -> pd.DataFrame:
    missing = [c for c in feature_columns if c not in X.columns]
    if missing:
        raise ValueError("Missing required anomaly-model features: " + ", ".join(missing))
    frame = X.loc[:, list(feature_columns)].copy()
    if not all(np.issubdtype(dtype, np.number) for dtype in frame.dtypes):
        raise TypeError("Anomaly-model features must be numeric")
    values = frame.to_numpy(dtype=np.float32)
    if not np.isfinite(values).all():
        raise ValueError("Anomaly-model features must be finite")
    return frame


def _require_binary(values: Sequence[int], name: str) -> None:
    classes = set(np.asarray(values, dtype=np.int8).tolist())
    if classes != {0, 1}:
        raise ValueError(f"{name} labels must contain both classes; found {sorted(classes)}")


def choose_threshold(
    normal_scores: Sequence[float], *, false_positive_quantile: float = 0.99
) -> float:
    if not 0.5 < false_positive_quantile < 1:
        raise ValueError("false_positive_quantile must be between 0.5 and 1")
    scores = np.asarray(normal_scores, dtype=float)
    if scores.size == 0 or not np.isfinite(scores).all():
        raise ValueError("normal_scores must be a non-empty finite sequence")
    return float(np.quantile(scores, false_positive_quantile))


def anomaly_metrics(
    y_true: Sequence[int], scores: Sequence[float], threshold: float
) -> dict[str, float]:
    y = np.asarray(y_true, dtype=np.int8)
    s = np.asarray(scores, dtype=float)
    if len(y) != len(s):
        raise ValueError("y_true and scores must have the same length")
    _require_binary(y, "evaluation")
    predicted = (s >= threshold).astype(np.int8)
    return {
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "anomaly_rate": float(predicted.mean()),
        "threshold": float(threshold),
    }


@dataclass
class IsolationForestAnomalyModel:
    """Unsupervised anomaly detector trained on normal-operation reference data.

    The model stores a calibrated threshold separately from sklearn's internal
    contamination cutoff. Higher scores mean more anomalous behavior.
    """

    model: Any
    feature_columns: list[str]
    threshold: float
    normal_score_quantile: float = 0.99
    metadata: dict[str, Any] | None = None

    @classmethod
    def fit(
        cls,
        X_normal: pd.DataFrame,
        *,
        feature_columns: Sequence[str],
        n_estimators: int = 300,
        max_samples: int | str = "auto",
        max_features: float = 1.0,
        false_positive_quantile: float = 0.99,
        random_seed: int = 26249,
    ) -> "IsolationForestAnomalyModel":
        frame = _feature_frame(X_normal, feature_columns)
        if len(frame) < 32:
            raise ValueError("At least 32 normal-operation rows are required")
        if n_estimators <= 0:
            raise ValueError("n_estimators must be greater than zero")
        if not 0 < max_features <= 1:
            raise ValueError("max_features must be in (0, 1]")

        estimator = IsolationForest(
            n_estimators=n_estimators,
            max_samples=max_samples,
            max_features=max_features,
            contamination="auto",
            random_state=random_seed,
            n_jobs=-1,
        )
        estimator.fit(frame)

        # sklearn's score_samples is larger for more normal observations.
        normal_scores = -estimator.score_samples(frame)
        threshold = choose_threshold(
            normal_scores, false_positive_quantile=false_positive_quantile
        )

        metadata = {
            "model": "IsolationForest",
            "training_mode": "normal_operation_only",
            "score_direction": "higher_is_more_anomalous",
            "threshold_method": "normal_reference_quantile",
            "normal_score_quantile": false_positive_quantile,
            "feature_count": len(feature_columns),
            "n_estimators": n_estimators,
            "max_samples": max_samples,
            "max_features": max_features,
            "random_seed": random_seed,
            "training_rows": len(frame),
        }
        return cls(
            model=estimator,
            feature_columns=list(feature_columns),
            threshold=threshold,
            normal_score_quantile=false_positive_quantile,
            metadata=metadata,
        )

    def score_samples(self, X: pd.DataFrame) -> np.ndarray:
        frame = _feature_frame(X, self.feature_columns)
        # Negating sklearn's score makes the contract intuitive.
        return -self.model.score_samples(frame)

    def predict(self, X: pd.DataFrame, threshold: float | None = None) -> np.ndarray:
        cutoff = self.threshold if threshold is None else threshold
        if not np.isfinite(cutoff):
            raise ValueError("threshold must be finite")
        return (self.score_samples(X) >= cutoff).astype(np.int8)

    def evaluate(
        self,
        X: pd.DataFrame,
        y_true: Sequence[int],
        threshold: float | None = None,
    ) -> dict[str, float]:
        cutoff = self.threshold if threshold is None else threshold
        return anomaly_metrics(y_true, self.score_samples(X), cutoff)

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, target)

    @classmethod
    def load(cls, path: str | Path) -> "IsolationForestAnomalyModel":
        model = joblib.load(path)
        if not isinstance(model, cls):
            raise TypeError(
                f"Expected {cls.__name__}, received {type(model).__name__}"
            )
        return model
