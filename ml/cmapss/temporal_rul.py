"""LSTM and TCN sequence models for C-MAPSS RUL prediction.

The models consume the same scaled 30-cycle feature sequences as the existing
HistGradientBoosting baseline. No API integration is performed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error


def regression_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=np.float32)
    y_pred = np.maximum(0.0, np.asarray(y_pred, dtype=np.float32))
    err = y_pred - y_true
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "score": float(np.mean(np.exp(np.maximum(err, 0) / 13.0) - 1.0)),
    }


def _tf():
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise ImportError(
            "TensorFlow is required for LSTM/TCN training and inference. "
            "Install it in the project environment before running this feature."
        ) from exc
    return tf


def build_lstm(input_shape, seed=26249):
    tf = _tf()
    tf.keras.utils.set_random_seed(seed)
    inputs = tf.keras.Input(shape=input_shape, name="telemetry_sequence")
    x = tf.keras.layers.LSTM(96, return_sequences=True, dropout=0.15)(inputs)
    x = tf.keras.layers.LSTM(48, dropout=0.15)(x)
    x = tf.keras.layers.Dense(32, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.10)(x)
    outputs = tf.keras.layers.Dense(1, name="rul")(x)
    return tf.keras.Model(inputs, outputs, name="fleetavail_lstm_rul")


def _tcn_block(x, filters, kernel_size, dilation, dropout):
    tf = _tf()
    residual = x
    y = tf.keras.layers.Conv1D(
        filters, kernel_size, padding="causal", dilation_rate=dilation
    )(x)
    y = tf.keras.layers.LayerNormalization()(y)
    y = tf.keras.layers.Activation("relu")(y)
    y = tf.keras.layers.SpatialDropout1D(dropout)(y)
    y = tf.keras.layers.Conv1D(
        filters, kernel_size, padding="causal", dilation_rate=dilation
    )(y)
    y = tf.keras.layers.LayerNormalization()(y)
    if residual.shape[-1] != filters:
        residual = tf.keras.layers.Conv1D(filters, 1, padding="same")(residual)
    y = tf.keras.layers.Add()([residual, y])
    return tf.keras.layers.Activation("relu")(y)


def build_tcn(input_shape, seed=26249):
    tf = _tf()
    tf.keras.utils.set_random_seed(seed)
    inputs = tf.keras.Input(shape=input_shape, name="telemetry_sequence")
    x = inputs
    for dilation in (1, 2, 4, 8):
        x = _tcn_block(x, 64, 3, dilation, 0.10)
    x = tf.keras.layers.GlobalAveragePooling1D()(x)
    x = tf.keras.layers.Dense(32, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.10)(x)
    outputs = tf.keras.layers.Dense(1, name="rul")(x)
    return tf.keras.Model(inputs, outputs, name="fleetavail_tcn_rul")


@dataclass
class TemporalRULModel:
    architecture: str
    model: object
    feature_columns: list[str]
    window_size: int
    scaler: object | None = None

    def predict(self, X):
        pred = self.model.predict(X, verbose=0).reshape(-1)
        return np.maximum(0.0, pred)

    def evaluate(self, X, y):
        return regression_metrics(y, self.predict(X))

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save(path)

    @classmethod
    def load(cls, path, feature_columns, window_size, scaler=None, architecture=None):
        tf = _tf()
        model = tf.keras.models.load_model(path, compile=False)
        arch = architecture or model.name.replace("fleetavail_", "").replace("_rul", "")
        return cls(arch, model, list(feature_columns), window_size, scaler)


def compile_model(model, learning_rate=1e-3):
    tf = _tf()
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss=tf.keras.losses.Huber(delta=10.0),
        metrics=[tf.keras.metrics.MeanAbsoluteError(name="mae")],
    )
    return model


def fit_model(
    model,
    X_train,
    y_train,
    X_val,
    y_val,
    epochs=80,
    batch_size=128,
    patience=10,
):
    tf = _tf()
    compile_model(model)
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=patience, restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=max(3, patience // 2), min_lr=1e-6
        ),
    ]
    return model.fit(
        X_train,
        np.minimum(y_train, 125.0),
        validation_data=(X_val, np.minimum(y_val, 125.0)),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1,
    )


def save_metadata(path, metadata):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(metadata, indent=2))
