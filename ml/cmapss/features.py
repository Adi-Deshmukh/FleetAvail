import numpy as np,pandas as pd
from sklearn.preprocessing import StandardScaler
from .config import DEFAULT_SENSORS
def clean(df):
    x=df.copy()
    x=x.sort_values(["unit_id","cycle"]).reset_index(drop=True)
    x= x.replace([np.inf,-np.inf],np.nan)
    x[DEFAULT_SENSORS]=x.groupby("unit_id")[list(DEFAULT_SENSORS)].transform(lambda z:z.fillna(z.median()))
    x[DEFAULT_SENSORS]=x[DEFAULT_SENSORS].fillna(x[DEFAULT_SENSORS].median())
    return x
def drop_constant_features(train,test):
    candidates=[c for c in train.columns if c not in ["unit_id","cycle","rul"]]
    keep=[c for c in candidates if train[c].nunique(dropna=False)>1]
    return train[["unit_id","cycle","rul"]+keep].copy(),test[["unit_id","cycle","rul"]+keep].copy(),keep
def add_temporal_features(df,base_features,windows=(5,10,20)):
    out=df.copy()
    for col in base_features:
        g=out.groupby("unit_id")[col]
        out[f"{col}_delta"]=g.diff().fillna(0)
        for w in windows:
            out[f"{col}_ma{w}"]=g.transform(lambda s:s.rolling(w,min_periods=1).mean())
    return out
def fit_scaler(train,features):
    scaler=StandardScaler(); scaler.fit(train[features]); return scaler
def transform(df,features,scaler):
    out=df.copy(); out[features]=scaler.transform(out[features]); return out
