from dataclasses import dataclass
from pathlib import Path
@dataclass(frozen=True)
class CMapssConfig:
    window_size:int=30
    horizon:int=0
    train_fraction:float=.8
    random_seed:int=26249
    raw_dir:Path=Path("data/raw/cmapss")
    processed_dir:Path=Path("data/processed/cmapss")
    model_dir:Path=Path("models/cmapss")
FEATURES=tuple(["op_setting_1","op_setting_2","op_setting_3"]+[f"sensor_{i}" for i in range(1,22)])
DEFAULT_SENSORS=tuple(f"sensor_{i}" for i in range(1,22))
