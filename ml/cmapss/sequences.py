import numpy as np
def make_sequences(df,features,window_size=30):
    xs=[]; ys=[]; units=[]
    for uid,g in df.groupby("unit_id",sort=True):
        g=g.sort_values("cycle")
        x=g[features].to_numpy(dtype=np.float32); y=g["rul"].to_numpy(dtype=np.float32)
        if len(g)<window_size: continue
        for end in range(window_size,len(g)+1):
            xs.append(x[end-window_size:end]); ys.append(y[end-1]); units.append(uid)
    if not xs: raise ValueError("No sequences created. Reduce window_size or check the dataset.")
    return np.stack(xs),np.asarray(ys),np.asarray(units)
def last_sequences(df,features,window_size=30):
    xs=[]; units=[]
    for uid,g in df.groupby("unit_id",sort=True):
        g=g.sort_values("cycle"); x=g[features].to_numpy(dtype=np.float32)
        if len(g)<window_size: raise ValueError(f"Unit {uid} has fewer than {window_size} cycles.")
        xs.append(x[-window_size:]); units.append(uid)
    return np.stack(xs),np.asarray(units)
