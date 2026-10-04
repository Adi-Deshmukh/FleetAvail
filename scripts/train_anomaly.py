import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.cmapss.anomaly import IsolationForestAnomalyModel
from ml.cmapss.data import load_cmapss
from ml.cmapss.features import add_temporal_features, clean, drop_constant_features


def build_features(frame, base_features):
    frame = clean(frame)
    frame = frame[["unit_id", "cycle", "rul"] + list(base_features)].copy()
    frame = add_temporal_features(frame, base_features)
    return frame


def main():
    parser = argparse.ArgumentParser(
        description="Train FleetAvail Isolation Forest on normal-operation C-MAPSS reference data."
    )
    parser.add_argument(
        "--subset",
        default="FD001",
        choices=["FD001", "FD002", "FD003", "FD004"],
    )
    parser.add_argument("--raw-dir", default="data/raw/cmapss")
    parser.add_argument("--false-positive-quantile", type=float, default=0.99)
    parser.add_argument("--estimators", type=int, default=300)
    parser.add_argument("--seed", type=int, default=26249)
    parser.add_argument("--model-out", default=None)
    args = parser.parse_args()

    train_raw, _ = load_cmapss(Path(args.raw_dir), args.subset)
    train_raw, _, base_features = drop_constant_features(train_raw, train_raw.copy())
    train = build_features(train_raw, base_features)

    # The current C-MAPSS training split does not contain an explicit
    # normal-operation label. For this first unsupervised slice, treat rows
    # from the early, low-degradation region as the reference population.
    normal = train.loc[train["rul"] >= 125.0].copy()
    if len(normal) < 32:
        normal = train.nlargest(max(32, int(len(train) * 0.20)), "rul").copy()

    feature_columns = [
        c for c in train.columns if c not in {"unit_id", "cycle", "rul"}
    ]

    model = IsolationForestAnomalyModel.fit(
        normal,
        feature_columns=feature_columns,
        n_estimators=args.estimators,
        false_positive_quantile=args.false_positive_quantile,
        random_seed=args.seed,
    )
    model.metadata.update(
        {
            "dataset": args.subset,
            "base_features": base_features,
            "temporal_windows": [5, 10, 20],
            "reference_selection": "rul>=125_or_top_20_percent",
        }
    )

    output = Path(
        args.model_out or f"models/cmapss/{args.subset.lower()}_isolation_forest.joblib"
    )
    model.save(output)
    output.with_suffix(".json").write_text(
        json.dumps(model.metadata, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "model": str(output),
                "dataset": args.subset,
                "threshold": model.threshold,
                "normal_score_quantile": model.normal_score_quantile,
                "feature_count": len(feature_columns),
                "training_rows": len(normal),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
