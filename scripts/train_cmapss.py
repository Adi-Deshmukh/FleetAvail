import argparse,json
from pathlib import Path
from ml.cmapss.config import CMapssConfig
from ml.cmapss.data import load_cmapss
from ml.cmapss.features import clean,drop_constant_features,add_temporal_features,fit_scaler,transform
from ml.cmapss.sequences import make_sequences,last_sequences
from ml.cmapss.model import CMapssRULModel
def main():
 p=argparse.ArgumentParser(); p.add_argument("--subset",default="FD001",choices=["FD001","FD002","FD003","FD004"]); p.add_argument("--window",type=int,default=30); p.add_argument("--raw-dir",default="data/raw/cmapss"); p.add_argument("--model-out",default=None); args=p.parse_args()
 cfg=CMapssConfig(window_size=args.window,raw_dir=Path(args.raw_dir))
 train,test=load_cmapss(cfg.raw_dir,args.subset)
 train,test=clean(train),clean(test)
 train,test,base=drop_constant_features(train,test)
 train=add_temporal_features(train,base); test=add_temporal_features(test,base)
 features=[c for c in train.columns if c not in ["unit_id","cycle","rul"]]
 scaler=fit_scaler(train,features); train=transform(train,features,scaler); test=transform(test,features,scaler)
 X,y,_=make_sequences(train,features,args.window)
 Xt,yt,_=make_sequences(test,features,args.window)
 model=CMapssRULModel().fit(X,y,features,args.window,scaler)
 metrics=model.evaluate(Xt,yt)
 out=Path(args.model_out or f"models/cmapss/{args.subset.lower()}_rul.joblib"); model.save(out)
 meta={"dataset":args.subset,"window":args.window,"features":features,"metrics":metrics,"model":str(out)}
 out.with_suffix(".json").write_text(json.dumps(meta,indent=2))
 print(json.dumps(meta,indent=2))
if __name__=="__main__": main()
