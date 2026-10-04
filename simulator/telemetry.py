import random
from datetime import datetime, timezone
class TelemetrySimulator:
    def __init__(self,seed=26249): self.rng=random.Random(seed)
    def engine_sample(self,aircraft_id,cycle,degradation=0):
        return {"timestamp":datetime.now(timezone.utc).isoformat(),"aircraft_id":aircraft_id,"component":"ENGINE","cycle":cycle,"egt_c":round(650+150*degradation+self.rng.uniform(-5,5),2),"vibration_g":round(.12+.9*degradation+self.rng.uniform(-.02,.02),3),"oil_pressure_kpa":round(410-140*degradation+self.rng.uniform(-3,3),2)}
