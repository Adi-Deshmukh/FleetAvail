from pathlib import Path
import joblib,numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error,mean_squared_error
class CMapssRULModel:
    def __init__(self):
        self.model=HistGradientBoostingRegressor(max_iter=300,learning_rate=.05,max_leaf_nodes=31,l2_regularization=.1,random_state=26249)
        self.feature_columns=None; self.window_size=None; self.scaler=None
    @staticmethod
    def flatten(X):
        last=X[:,-1,:]; mean=X.mean(axis=1); std=X.std(axis=1); delta=X[:,-1,:]-X[:,0,:]
        return np.concatenate([last,mean,std,delta],axis=1)
    def fit(self,X,y,feature_columns,window_size,scaler=None):
        self.feature_columns=list(feature_columns); self.window_size=window_size; self.scaler=scaler
        self.model.fit(self.flatten(X),np.minimum(y,125.0)); return self
    def predict(self,X):
        return np.maximum(0,self.model.predict(self.flatten(X)))
    def evaluate(self,X,y):
        p=self.predict(X); err=p-y
        return {"mae":float(mean_absolute_error(y,p)),"rmse":float(np.sqrt(mean_squared_error(y,p))),"score":float(np.mean(np.exp(np.maximum(err,0)/13)-1))}
    def save(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True); joblib.dump(self,path)
    @classmethod
    def load(cls,path): return joblib.load(path)
