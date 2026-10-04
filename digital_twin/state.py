from dataclasses import dataclass, field
from typing import Dict
@dataclass
class ComponentState:
    name: str
    health: float = 1.0
    degradation: float = 0.0
    rul_cycles: float = 100.0
    failure_probability: float = 0.0
    last_update_cycle: int = 0
@dataclass
class AircraftTwin:
    aircraft_id: str
    components: Dict[str, ComponentState] = field(default_factory=dict)
    def apply_degradation(self, component: str, percentage: float):
        state=self.components[component]; factor=max(0.0,1.0-percentage/100.0)
        state.health=max(0.0,min(1.0,state.health*factor)); state.degradation=1-state.health
        state.rul_cycles=max(1.0,state.rul_cycles*factor)
        state.failure_probability=min(.99,state.failure_probability+max(0,percentage)/130)
        return state
