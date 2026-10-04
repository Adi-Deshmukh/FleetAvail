import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.cmapss.data import load_cmapss
from ml.cmapss.failure import (
    XGBoostFailureRiskModel,
    add_failure_label,
    engine_aware_split,
)
from ml.cmapss.features import add_temporal_features, clean, drop_constant_features


def preprocess_training_splits(train_raw, calibration_raw, holdout_raw):
    train = clean(train_raw)
    calibration = clean(calibration_raw)
    holdout = clean(holdout_raw)

    train, calibration, base_features = drop_constant_features(train, calibration)
    holdout = holdout[["unit_id", "cycle", "rul"] + base_features].copy()

    train = add_temporal_features(train, base_features)
    calibration = add_temporal_features(calibration, base_features)
    holdout = add_temporal_features(holdout, base_features)

    feature_columns = [
        c for c in train.columns
        if c not in {"unit_id", "cycle", "rul"}
    ]
    train = add_failure_label(train)
    calibration = add_failure_label(calibration)
    holdout = add_failure_label(holdout)
    return train, calibration, holdout, base_features, feature_columns


def preprocess_official_test(test_raw, base_features):
    test = clean(test_raw)
    test = test[["unit_id", "cycle", "rul"] + base_features].copy()
    return add_temporal_features(test, base_features)


def main():
    parser = argparse.ArgumentParser(
        description="Train the FleetAvail XGBoost failure-risk model on NASA C-MAPSS."
    )
    parser.add_argument("--subset", default="FD001", choices=["FD001", "FD002", "FD003", "FD004"])
    parser.add_argument("--horizon", type=int, default=30)
    parser.add_argument("--raw-dir", default="data/raw/cmapss")
    parser.add_argument("--test-fraction", type=float, default=0.20)
    parser.add_argument("--calibration-fraction", type=float, default=0.20)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=26249)
    parser.add_argument("--model-out", default=None)
    args = parser.parse_args()

    if args.horizon <= 0:
        raise ValueError("--horizon must be greater than zero")

    raw_train, raw_test = load_cmapss(Path(args.raw_dir), args.subset)
    train_raw, calibration_raw, holdout_raw = engine_aware_split(
        raw_train,
        calibration_fraction=args.calibration_fraction,
        test_fraction=args.test_fraction,
        random_seed=args.seed,
    )

    train, calibration, holdout, base_features, feature_columns = preprocess_training_splits(
        train_raw, calibration_raw, holdout_raw
    )

    model = XGBoostFailureRiskModel.fit(
        train,
        train["failure_within_horizon"],
        calibration,
        calibration["failure_within_horizon"],
        feature_columns=feature_columns,
        horizon=args.horizon,
        threshold=args.threshold,
        random_seed=args.seed,
    )

    holdout_metrics = model.evaluate(
        holdout,
        holdout["failure_within_horizon"],
    )

    model.horizon = args.horizon
    model.metadata.update({
        "dataset": args.subset,
        "base_features": base_features,
        "temporal_windows": [5, 10, 20],
        "engine_aware_split": True,
        "calibration_fraction": args.calibration_fraction,
        "holdout_fraction": args.test_fraction,
        "holdout_metrics": holdout_metrics,
    })

    official_test = preprocess_official_test(raw_test, base_features)
    official_test = add_failure_label(official_test, args.horizon)
    official_metrics = model.evaluate(
        official_test,
        official_test["failure_within_horizon"],
    )
    model.metadata["official_test_metrics"] = official_metrics

    output = Path(
        args.model_out
        or f"models/cmapss/{args.subset.lower()}_failure.joblib"
    )
    model.save(output)
    output.with_suffix(".json").write_text(
        json.dumps(model.metadata, indent=2),
        encoding="utf-8",
    )

    print(json.dumps({
        "model": str(output),
        "dataset": args.subset,
        "horizon_cycles": args.horizon,
        "holdout_metrics": holdout_metrics,
        "official_test_metrics": official_metrics,
        "feature_count": len(feature_columns),
    }, indent=2))


if __name__ == "__main__":
    main()
