from dataclasses import dataclass
@dataclass
class MaintenanceDecision:
    component: str
    priority_score: float
    action: str
    reason_codes: list[str]
def rank_component(component,failure_probability,rul_cycles,mission_priority,spare_available):
    urgency=1/(1+max(0,rul_cycles))
    score=failure_probability*.65+urgency*8+(2-mission_priority)*.15
    action="ORDER_SPARE_AND_SCHEDULE" if not spare_available else ("SCHEDULE_MAINTENANCE" if failure_probability>=.6 or rul_cycles<45 else "CONTINUE_MONITORING")
    return MaintenanceDecision(component,round(score,3),action,["FAILURE_RISK","RUL_URGENCY","MISSION_PRIORITY","SPARE_AVAILABILITY"])
