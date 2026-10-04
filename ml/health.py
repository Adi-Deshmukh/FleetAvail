"""Replaceable health-fusion layer."""
def fuse_health(health, anomaly, data_quality, risk, rul):
    score = 100 * (0.50 * health + 0.25 * (1.0 - anomaly) + 0.25 * data_quality)
    level = "CRITICAL" if risk >= 0.85 or rul < 20 else ("WARNING" if risk >= 0.60 or rul < 45 else "SAFE")
    return {"health_score":round(score,1),"failure_probability":round(risk,3),"anomaly_score":round(anomaly,3),"rul_cycles":round(rul,1),"data_quality":round(data_quality,3),"alert_level":level}
