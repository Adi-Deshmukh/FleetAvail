from pathlib import Path
import numpy as np,pandas as pd
from .config import FEATURES,DEFAULT_SENSORS,CMapssConfig
COLUMN_NAMES=["unit_id","cycle","op_setting_1","op_setting_2","op_setting_3"]+list(DEFAULT_SENSORS)
def read_txt(path):
    df=pd.read_csv(path,sep=r"\s+",header=None)
    df=df.iloc[:,:26]; df.columns=COLUMN_NAMES
    return df
def load_split(root,split):
    root=Path(root); path=root/f"{split}.txt"
    if not path.exists(): raise FileNotFoundError(f"Missing {path}. Download the official NASA C-MAPSS dataset and place it under data/raw/cmapss/.")
    return read_txt(path)
def load_rul(root,split):
    path=Path(root)/f"{split}.txt"
    if not path.exists(): raise FileNotFoundError(f"Missing {path}")
    return pd.read_csv(path,header=None,names=["rul"])
def add_train_rul(df):
    out=df.copy()
    max_cycles=out.groupby("unit_id")["cycle"].transform("max")
    out["rul"]=max_cycles-out["cycle"]
    return out
def add_test_rul(df,rul):
    out=df.copy(); out["rul"]=0.0
    last=out.groupby("unit_id")["cycle"].transform("max")
    mapping=dict(zip(sorted(out.unit_id.unique()),rul["rul"].astype(float)))
    out["rul"]=last-out["cycle"]+out["unit_id"].map(mapping)
    return out
def load_cmapss(root,subset="FD001"):
    root=Path(root)/subset
    train=load_split(root,"train"); test=load_split(root,"test"); rul=load_rul(root,"RUL_test")
    return add_train_rul(train),add_test_rul(test,rul)
def select_features(df):
    return df.loc[:,FEATURES].copy()
