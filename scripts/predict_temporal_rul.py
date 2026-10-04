import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
import joblib

from ml.cmapss.data import load_cmapss
from ml.cmapss.features import clean, drop_constant_features, add_temporal_features, transform
from ml.cmapss.sequences import last_sequences
from ml.cmapss.temporal_rul import TemporalRULModel


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--subset", default="FD001")
    p.add_argument("--architecture", default="lstm", choices=["lstm", "tcn"])
    p.add_argument("--raw-dir", default="data/raw/cmapss")
    p.add_argument("--model-dir", default="models/cmapss")
    args = p.parse_args()

    model_path = Path(args.model_dir) / f"{args.subset.lower()}_{args.architecture}_rul.keras"
    meta_path = model_path.with_suffix(".json")
    meta = json.loads(meta_path.read_text())
    scaler = joblib.load(meta["scaler"])
    model = TemporalRULModel.load(
        model_path,
        meta["features"],
        meta["window"],
        scaler=scaler,
        architecture=args.architecture,
    )

    _, test = load_cmapss(Path(args.raw_dir), args.subset)
    test = clean(test)
    features = model.feature_columns
    raw_features = [c for c in features if "_delta" not in c and "_ma" not in c]
    test = test[["unit_id", "cycle", "rul"] + raw_features]
    test = add_temporal_features(test, raw_features)
    test = transform(test, features, model.scaler)

    X, units = last_sequences(test, features, model.window_size)
    preds = model.predict(X)
    print(json.dumps([
        {"unit_id": int(u), "predicted_rul": round(float(r), 2)}
        for u, r in zip(units, preds)
    ], indent=2))


if __name__ == "__main__":
    main()
