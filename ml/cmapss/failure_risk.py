from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from xgboost import XGBClassifier


def add_failure_label(df: pd.DataFrame, horizon: int = 30) -> pd.DataFrame:
    """Mark rows whose RUL is within the chosen failure horizon."""
    if horizon <= 0:
        raise ValueError("horizon must be greater than zero")
    if "rul" not in df.columns:
        raise ValueError("DataFrame must contain a 'rul' column")
    result = df.copy()
    result["failure_within_horizon"] = (
        result["rul"].astype(float) <= float(horizon)
    ).astype(np.int8)
    return result


def _require_binary(values: Sequence[int], name: str) -> None:
    classes = set(np.asarray(values, dtype=np.int8).tolist())
    if classes != {0, 1}:
        raise ValueError(
            f"{name} split must contain both classes; found {sorted(classes)}"
        )


def engine_aware_split(
    df: pd.DataFrame,
    *,
    calibration_fraction: float = 0.20,
    test_fraction: float = 0.20,
    random_seed: int = 26249,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split complete engine trajectories; no engine is shared across splits."""
    if not 0 < calibration_fraction < 1:
        raise ValueError("calibration_fraction must be between 0 and 1")
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")
    if calibration_fraction + test_fraction >= 1:
        raise ValueError("calibration_fraction + test_fraction must be less than 1")
    if "unit_id" not in df.columns:
        raise ValueError("DataFrame must contain 'unit_id'")

    groups = df["unit_id"].to_numpy()
    first = GroupShuffleSplit(
        n_splits=1, test_size=test_fraction, random_state=random_seed
    )
    train_cal_idx, test_idx = next(first.split(df, groups=groups))
    train_cal = df.iloc[train_cal_idx].copy()
    test = df.iloc[test_idx].copy()

    relative_cal = calibration_fraction / (1.0 - test_fraction)
    second = GroupShuffleSplit(
        n_splits=1, test_size=relative_cal, random_state=random_seed + 1
    )
    train_idx, calibration_idx = next(
        second.split(train_cal, groups=train_cal["unit_id"].to_numpy())
    )
    train = train_cal.iloc[train_idx].copy()
    calibration = train_cal.iloc[calibration_idx].copy()

    for frame in (train, calibration, test):
        frame.sort_values(["unit_id", "cycle"], inplace=True)
    return train, calibration, test


def _feature_frame(
    X: pd.DataFrame, feature_columns: Sequence[str]
) -> pd.DataFrame:
    missing = [c for c in feature_columns if c not in X.columns]
    if missing:
        raise ValueError("Missing required failure-model features: " + ", ".join(missing))
    frame = X.loc[:, list(feature_columns)].copy()
    if not all(np.issubdtype(dtype, np.number) for dtype in frame.dtypes):
        raise TypeError("Failure-model features must be numeric")
    values = frame.to_numpy(dtype=np.float32)
    if not np.isfinite(values).all():
        raise ValueError("Failure-model features must be finite")
    return frame


def classification_metrics(
    y_true: Sequence[int],
    probabilities: Sequence[float],
    threshold: float = 0.5,
) -> dict[str, float]:
    """Return probability quality and thresholded classification metrics."""
    if not 0 < threshold < 1:
        raise ValueError("threshold must be between 0 and 1")
    y = np.asarray(y_true, dtype=np.int8)
    p = np.clip(np.asarray(probabilities, dtype=float), 0.0, 1.0)
    _require_binary(y, "evaluation")
    predicted = (p >= threshold).astype(np.int8)
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "average_precision": float(average_precision_score(y, p)),
        "brier_score": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "positive_rate": float(predicted.mean()),
        "threshold": float(threshold),
    }


@dataclass
class XGBoostFailureRiskModel:
    """XGBoost classifier plus a held-out sigmoid probability calibrator."""

    model: Any
    calibrator: LogisticRegression
    feature_columns: list[str]
    horizon: int
    threshold: float = 0.5
    metadata: dict[str, Any] | None = None

    @classmethod
    def fit(
        cls,
        X_train: pd.DataFrame,
        y_train: Sequence[int],
        X_calibration: pd.DataFrame,
        y_calibration: Sequence[int],
        *,
        feature_columns: Sequence[str],
        horizon: int,
        threshold: float = 0.5,
        random_seed: int = 26249,
    ) -> "XGBoostFailureRiskModel":
        if horizon <= 0:
            raise ValueError("horizon must be greater than zero")
        if not 0 < threshold < 1:
            raise ValueError("threshold must be between 0 and 1")

        train = _feature_frame(X_train, feature_columns)
        calibration = _feature_frame(X_calibration, feature_columns)
        ytr = np.asarray(y_train, dtype=np.int8)
        ycal = np.asarray(y_calibration, dtype=np.int8)
        _require_binary(ytr, "train")
        _require_binary(ycal, "calibration")

        positives = max(1, int(ytr.sum()))
        negatives = max(1, int(len(ytr) - ytr.sum()))
        scale_pos_weight = negatives / positives

        estimator = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.8,
            min_child_weight=2,
            reg_lambda=2.0,
            scale_pos_weight=scale_pos_weight,
            random_state=random_seed,
            n_jobs=2,
            verbosity=0,
        )
        estimator.fit(train, ytr)

        raw = np.clip(estimator.predict_proba(calibration)[:, 1], 1e-6, 1 - 1e-6)
        logits = np.log(raw / (1.0 - raw)).reshape(-1, 1)

        calibrator = LogisticRegression(solver="lbfgs", random_state=random_seed)
        calibrator.fit(logits, ycal)

        metadata = {
            "model": "XGBClassifier",
            "calibration": "sigmoid_platt_on_held_out_engines",
            "horizon_cycles": horizon,
            "threshold": threshold,
            "feature_count": len(feature_columns),
            "scale_pos_weight": float(scale_pos_weight),
            "random_seed": random_seed,
        }
        return cls(
            estimator,
            calibrator,
            list(feature_columns),
            horizon,
            threshold,
            metadata,
        )

    @staticmethod
    def _logit(probabilities: np.ndarray) -> np.ndarray:
        p = np.clip(probabilities, 1e-6, 1 - 1e-6)
        return np.log(p / (1.0 - p))

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        frame = _feature_frame(X, self.feature_columns)
        raw = self.model.predict_proba(frame)[:, 1]
        return np.clip(
            self.calibrator.predict_proba(self._logit(raw).reshape(-1, 1))[:, 1],
            0.0,
            1.0,
        )

    def predict(
        self, X: pd.DataFrame, threshold: float | None = None
    ) -> np.ndarray:
        cutoff = self.threshold if threshold is None else threshold
        if not 0 < cutoff < 1:
            raise ValueError("threshold must be between 0 and 1")
        return (self.predict_proba(X) >= cutoff).astype(np.int8)

    def evaluate(
        self,
        X: pd.DataFrame,
        y_true: Sequence[int],
        threshold: float | None = None,
    ) -> dict[str, float]:
        cutoff = self.threshold if threshold is None else threshold
        return classification_metrics(y_true, self.predict_proba(X), cutoff)

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, target)

    @classmethod
    def load(cls, path: str | Path) -> "XGBoostFailureRiskModel":
        model = joblib.load(path)
        if not isinstance(model, cls):
            raise TypeError(
                f"Expected {cls.__name__}, received {type(model).__name__}"
            )
        return model
