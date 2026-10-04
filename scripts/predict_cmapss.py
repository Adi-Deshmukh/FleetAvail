import argparse,json
from pathlib import Path
from ml.cmapss.data import load_cmapss
from ml.cmapss.features import clean,drop_constant_features,add_temporal_features,transform
from ml.cmapss.sequences import last_sequences
from ml.cmapss.model import CMapssRULModel
def main():
 p=argparse.ArgumentParser(); p.add_argument("--subset",default="FD001"); p.add_argument("--raw-dir",default="data/raw/cmapss"); p.add_argument("--model",default=None); a=p.parse_args()
 path=Path(a.model or f"models/cmapss/{a.subset.lower()}_rul.joblib"); model=CMapssRULModel.load(path)
 _,test,_=load_cmapss(Path(a.raw_dir),a.subset)
 test=clean(test)
 features=model.feature_columns
 raw_features=[c for c in features if "_delta" not in c and "_ma" not in c]
 test=test[["unit_id","cycle","rul"]+raw_features]
 test=add_temporal_features(test,raw_features)
 test=transform(test,features,model.scaler)
 X,units=last_sequences(test,features,model.window_size)
 preds=model.predict(X)
 print(json.dumps([{"unit_id":int(u),"predicted_rul":round(float(r),2)} for u,r in zip(units,preds)],indent=2))
if __name__=="__main__": main()
