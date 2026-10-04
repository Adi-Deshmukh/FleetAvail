import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.cmapss.anomaly import IsolationForestAnomalyModel
from ml.cmapss.data import load_cmapss
from ml.cmapss.features import add_temporal_features, clean


def main():
    parser = argparse.ArgumentParser(
        description="Score C-MAPSS telemetry with a trained Isolation Forest."
    )
    parser.add_argument("--subset", default="FD001")
    parser.add_argument("--raw-dir", default="data/raw/cmapss")
    parser.add_argument("--model", default=None)
    parser.add_argument("--threshold", type=float, default=None)
    args = parser.parse_args()

    model_path = Path(
        args.model or f"models/cmapss/{args.subset.lower()}_isolation_forest.joblib"
    )
    model = IsolationForestAnomalyModel.load(model_path)

    _, raw_test = load_cmapss(Path(args.raw_dir), args.subset)
    base_features = list((model.metadata or {}).get("base_features", []))
    if not base_features:
        raise ValueError("Model metadata does not contain base_features")

    test = clean(raw_test)
    test = test[["unit_id", "cycle", "rul"] + base_features].copy()
    test = add_temporal_features(test, base_features)

    scores = model.score_samples(test)
    predictions = model.predict(test, threshold=args.threshold)

    terminal = (
        test.sort_values(["unit_id", "cycle"])
        .groupby("unit_id", sort=True)
        .tail(1)
        .copy()
    )
    terminal["anomaly_score"] = scores[terminal.index]
    terminal["is_anomaly"] = predictions[terminal.index]

    rows = [
        {
            "unit_id": int(row.unit_id),
            "cycle": int(row.cycle),
            "actual_rul": float(row.rul),
            "anomaly_score": round(float(row.anomaly_score), 6),
            "is_anomaly": int(row.is_anomaly),
        }
        for row in terminal.itertuples()
    ]
    cutoff = model.threshold if args.threshold is None else args.threshold

    print(
        json.dumps(
            {
                "model": str(model_path),
                "threshold": cutoff,
                "score_direction": "higher_is_more_anomalous",
                "terminal_engine_scores": rows,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
