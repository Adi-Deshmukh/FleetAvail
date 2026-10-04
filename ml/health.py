"""Operational health fusion for FleetAvail."""
from __future__ import annotations


def fuse_health(
    health: float,
    anomaly: float,
    data_quality: float,
    risk: float,
    rul: float,
):
    health = max(0.0, min(1.0, float(health)))
    anomaly = max(0.0, min(1.0, float(anomaly)))
    data_quality = max(0.0, min(1.0, float(data_quality)))
    risk = max(0.0, min(1.0, float(risk)))
    rul = max(0.0, float(rul))

    # RUL is represented separately, while health is the normalized fused signal.
    score = 100.0 * (
        0.40 * health
        + 0.25 * (1.0 - anomaly)
        + 0.20 * (1.0 - risk)
        + 0.15 * data_quality
    )

    if risk >= 0.85 or rul < 20 or anomaly >= 0.90:
        state = "CRITICAL"
    elif risk >= 0.60 or rul < 45 or anomaly >= 0.70:
        state = "DEGRADED"
    elif risk >= 0.30 or rul < 90 or anomaly >= 0.45:
        state = "WATCH"
    else:
        state = "NORMAL"

    return {
        "health_score": round(max(0.0, min(100.0, score)), 1),
        "failure_probability": round(risk, 4),
        "anomaly_score": round(anomaly, 4),
        "rul_cycles": round(rul, 1),
        "data_quality": round(data_quality, 3),
        "operational_state": state,
        # Kept for compatibility with the existing dashboard/API consumers.
        "alert_level": state,
    }
