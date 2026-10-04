import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.cmapss.data import load_cmapss
from ml.cmapss.failure_risk import XGBoostFailureRiskModel, add_failure_label
from ml.cmapss.features import add_temporal_features, clean


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a trained FleetAvail XGBoost failure-risk model on C-MAPSS."
    )
    parser.add_argument("--subset", default="FD001")
    parser.add_argument("--raw-dir", default="data/raw/cmapss")
    parser.add_argument("--model", default=None)
    parser.add_argument("--threshold", type=float, default=None)
    args = parser.parse_args()

    model_path = Path(
        args.model or f"models/cmapss/{args.subset.lower()}_failure.joblib"
    )
    model = XGBoostFailureRiskModel.load(model_path)

    _, raw_test = load_cmapss(Path(args.raw_dir), args.subset)
    base_features = list((model.metadata or {}).get("base_features", []))
    if not base_features:
        raise ValueError("Model metadata does not contain base_features")

    test = clean(raw_test)
    missing = [c for c in base_features if c not in test.columns]
    if missing:
        raise ValueError("Test data is missing base features: " + ", ".join(missing))
    test = test[["unit_id", "cycle", "rul"] + base_features].copy()
    test = add_temporal_features(test, base_features)
    test = add_failure_label(test, model.horizon)

    probabilities = model.predict_proba(test)
    probability_by_index = probabilities
    metrics = model.evaluate(
        test,
        test["failure_within_horizon"],
        threshold=args.threshold,
    )

    terminal = (
        test.sort_values(["unit_id", "cycle"])
        .groupby("unit_id", sort=True)
        .tail(1)
        .copy()
    )
    terminal_positions = terminal.index.to_numpy()
    terminal["failure_probability"] = probability_by_index[terminal_positions]
    cutoff = model.threshold if args.threshold is None else args.threshold
    terminal["predicted_failure"] = (
        terminal["failure_probability"] >= cutoff
    ).astype(int)

    rows = [
        {
            "unit_id": int(row.unit_id),
            "cycle": int(row.cycle),
            "actual_rul": float(row.rul),
            "failure_probability": round(float(row.failure_probability), 4),
            "predicted_failure": int(row.predicted_failure),
        }
        for row in terminal.itertuples()
    ]

    print(
        json.dumps(
            {
                "model": str(model_path),
                "horizon_cycles": model.horizon,
                "metrics": metrics,
                "terminal_engine_predictions": rows,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
