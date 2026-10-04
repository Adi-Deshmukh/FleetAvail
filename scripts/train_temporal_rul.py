import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
import numpy as np

from ml.cmapss.config import CMapssConfig
from ml.cmapss.data import load_cmapss
from ml.cmapss.features import (
    clean,
    drop_constant_features,
    add_temporal_features,
    fit_scaler,
    transform,
)
from ml.cmapss.sequences import make_sequences
from ml.cmapss.temporal_rul import (
    build_lstm,
    build_tcn,
    fit_model,
    regression_metrics,
    save_metadata,
    TemporalRULModel,
)


def preprocess(train, test):
    train, test = clean(train), clean(test)
    train, test, base = drop_constant_features(train, test)
    train = add_temporal_features(train, base)
    test = add_temporal_features(test, base)
    features = [c for c in train.columns if c not in ["unit_id", "cycle", "rul"]]
    scaler = fit_scaler(train, features)
    train = transform(train, features, scaler)
    test = transform(test, features, scaler)
    return train, test, features, scaler


def split_by_engine(df, fraction, seed):
    units = np.array(sorted(df.unit_id.unique()))
    rng = np.random.default_rng(seed)
    rng.shuffle(units)
    cut = max(1, int(len(units) * fraction))
    return set(units[:cut]), set(units[cut:])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--subset", default="FD001", choices=["FD001", "FD002", "FD003", "FD004"])
    p.add_argument("--architecture", default="both", choices=["lstm", "tcn", "both"])
    p.add_argument("--window", type=int, default=30)
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--raw-dir", default="data/raw/cmapss")
    p.add_argument("--model-dir", default="models/cmapss")
    args = p.parse_args()

    cfg = CMapssConfig(window_size=args.window, raw_dir=Path(args.raw_dir))
    train, test = load_cmapss(cfg.raw_dir, args.subset)
    train, test, features, scaler = preprocess(train, test)

    train_units, val_units = split_by_engine(train, 0.8, cfg.random_seed)
    train_part = train[train.unit_id.isin(train_units)]
    val_part = train[train.unit_id.isin(val_units)]

    X_train, y_train, _ = make_sequences(train_part, features, args.window)
    X_val, y_val, _ = make_sequences(val_part, features, args.window)
    X_test, y_test, _ = make_sequences(test, features, args.window)

    architectures = ["lstm", "tcn"] if args.architecture == "both" else [args.architecture]
    results = {}

    for arch in architectures:
        builder = build_lstm if arch == "lstm" else build_tcn
        model = builder((X_train.shape[1], X_train.shape[2]), seed=cfg.random_seed)
        history = fit_model(
            model, X_train, y_train, X_val, y_val,
            epochs=args.epochs, batch_size=args.batch_size
        )
        wrapped = TemporalRULModel(arch, model, features, args.window, scaler)
        metrics = regression_metrics(y_test, wrapped.predict(X_test))
        val_metrics = regression_metrics(y_val, wrapped.predict(X_val))
        out = Path(args.model_dir) / f"{args.subset.lower()}_{arch}_rul.keras"
        wrapped.save(out)
        meta = {
            "dataset": args.subset,
            "architecture": arch,
            "window": args.window,
            "features": features,
            "feature_count": len(features),
            "train_engines": len(train_units),
            "validation_engines": len(val_units),
            "epochs_requested": args.epochs,
            "epochs_completed": len(history.history["loss"]),
            "batch_size": args.batch_size,
            "validation_metrics": val_metrics,
            "test_metrics": metrics,
            "model": str(out),
            "baseline_comparison_required": True,
            "baseline": "HistGradientBoosting",
        }
        save_metadata(out.with_suffix(".json"), meta)
        results[arch] = meta

    comparison = {
        "dataset": args.subset,
        "window": args.window,
        "baseline_comparison": "Compare test MAE/RMSE/score against fd001_rul.json before replacement.",
        "models": {
            arch: {
                "mae": meta["test_metrics"]["mae"],
                "rmse": meta["test_metrics"]["rmse"],
                "score": meta["test_metrics"]["score"],
            }
            for arch, meta in results.items()
        },
    }
    save_metadata(Path(args.model_dir) / f"{args.subset.lower()}_temporal_rul_comparison.json", comparison)
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()
