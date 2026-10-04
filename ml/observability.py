"""Operational observability, provenance, audit, drift and local explanations."""
from __future__ import annotations
from collections import defaultdict, deque
from datetime import datetime, timezone
import math
import statistics
from typing import Any, Mapping

PHASE_C_VERSION = "phase-c-v1"
PREDICTION_STATUSES = {"COLD_START", "READY", "DEGRADED_DATA", "ERROR"}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False

class PredictionObservability:
    def __init__(self, *, max_audit_records: int = 500, max_history: int = 200):
        self.audit = deque(maxlen=max_audit_records)
        self.latencies = deque(maxlen=max_history)
        self.outputs: dict[tuple[str, str], deque[dict[str, float]]] = defaultdict(lambda: deque(maxlen=max_history))
        self.input_references: dict[tuple[str, str], dict[str, tuple[float, float]]] = {}
        self.counts = defaultdict(int)
        self.total = 0

    @staticmethod
    def input_quality(telemetry: Mapping[str, Any], *, sensor_count: int = 21) -> dict[str, Any]:
        required = ["op_setting_1", "op_setting_2", "op_setting_3"] + [f"sensor_{i}" for i in range(1, sensor_count + 1)]
        aliases = {"sensor_2": "egt_c", "sensor_3": "vibration_g", "sensor_4": "oil_pressure_kpa"}
        missing, invalid = [], []
        for key in required:
            value = telemetry.get(key)
            if value is None and key in aliases:
                value = telemetry.get(aliases[key])
            if value is None:
                missing.append(key)
            elif not _finite(value):
                invalid.append(key)
        quality = max(0.0, 1.0 - (len(missing) + len(invalid)) / len(required))
        return {"score": round(quality, 3), "missing_fields": missing, "invalid_fields": invalid, "required_fields": len(required)}

    def _set_reference(self, key, rows):
        if key in self.input_references or len(rows) < 2:
            return
        names = ["op_setting_1", "op_setting_2", "op_setting_3"] + [f"sensor_{i}" for i in range(1, 22)]
        reference = {}
        for name in names:
            values = [float(r[name]) for r in rows if name in r and _finite(r[name])]
            if len(values) >= 2:
                mean = statistics.fmean(values)
                std = statistics.pstdev(values) or max(abs(mean) * .01, 1e-6)
                reference[name] = (mean, std)
        if reference:
            self.input_references[key] = reference

    def drift(self, aircraft_id, component, telemetry, *, history=None, failure_probability=None, rul_cycles=None):
        key = (aircraft_id, component)
        if history:
            self._set_reference(key, history)
        ref = self.input_references.get(key, {})
        flags, max_z = [], 0.0
        for name, (mean, std) in ref.items():
            value = telemetry.get(name)
            if value is None or not _finite(value):
                continue
            z = abs(float(value) - mean) / max(std, 1e-6)
            max_z = max(max_z, z)
            if z >= 3.0:
                flags.append(name)
        history_outputs = self.outputs[key]
        output_drift = False
        if history_outputs and failure_probability is not None:
            baseline = statistics.fmean(x["failure_probability"] for x in history_outputs)
            output_drift = abs(float(failure_probability) - baseline) >= .20
        if history_outputs and rul_cycles is not None:
            ruls = [x["rul_cycles"] for x in history_outputs if x["rul_cycles"] >= 0]
            if ruls:
                baseline = statistics.fmean(ruls)
                output_drift = output_drift or abs(float(rul_cycles) - baseline) >= max(20.0, baseline * .35)
        return {
            "input_drift": {"detected": bool(flags), "max_z_score": round(max_z, 3), "flagged_features": flags[:10], "method": "reference_window_z_score"},
            "prediction_drift": {"detected": output_drift, "method": "rolling_output_shift"},
            "overall_drift": bool(flags or output_drift),
        }

    def explain(self, telemetry, *, history=None, failure_probability=None, rul_cycles=None, anomaly_score=None):
        rows = history or []
        scores = []
        for name in [f"sensor_{i}" for i in range(1, 22)]:
            values = [float(r[name]) for r in rows if name in r and _finite(r[name])]
            value = telemetry.get(name)
            if value is None or not _finite(value) or len(values) < 2:
                continue
            mean = statistics.fmean(values)
            std = statistics.pstdev(values) or max(abs(mean) * .01, 1e-6)
            z = (float(value) - mean) / std
            scores.append((abs(z), name, z))
        scores.sort(reverse=True)
        top = [{"feature": n, "z_score": round(z, 3), "magnitude": round(m, 3), "direction": "above_reference" if z > 0 else "below_reference"} for m, n, z in scores[:5]]
        reasons = []
        if failure_probability is not None and failure_probability >= .60:
            reasons.append("failure-risk signal is elevated")
        if rul_cycles is not None and rul_cycles <= 45:
            reasons.append("remaining useful life is short")
        if anomaly_score is not None and anomaly_score >= .70:
            reasons.append("anomaly signal is elevated")
        return {
            "method": "local_signal_attribution",
            "status": "available" if top or reasons else "limited",
            "limitations": ["This is a model-agnostic local explanation.", "It is not a SHAP value and must not be interpreted as causal attribution."],
            "top_signals": top,
            "decision_reasons": reasons,
        }

    def record(self, *, aircraft_id, component, cycle, telemetry_quality, prediction, provenance, latency_ms, status, explanation=None, drift=None, error=None):
        if status not in PREDICTION_STATUSES:
            raise ValueError(f"Unsupported prediction status: {status}")
        self.total += 1
        self.counts["total"] += 1
        self.counts[status.lower()] += 1
        self.latencies.append(float(latency_ms))
        if status == "ERROR": self.counts["errors"] += 1
        if telemetry_quality.get("score", 1.0) < .80: self.counts["quality_degraded"] += 1
        if status == "COLD_START": self.counts["cold_start"] += 1
        risk, rul, anomaly = prediction.get("failure_probability"), prediction.get("rul_cycles"), prediction.get("anomaly_score")
        if risk is not None and rul is not None:
            self.outputs[(aircraft_id, component)].append({"failure_probability": float(risk), "rul_cycles": float(rul), "anomaly_score": float(anomaly or 0)})
        self.audit.append({
            "timestamp": _now(), "phase_c_version": PHASE_C_VERSION,
            "aircraft_id": aircraft_id, "component": component, "cycle": int(cycle),
            "status": status, "latency_ms": round(float(latency_ms), 3),
            "telemetry_quality": dict(telemetry_quality),
            "prediction": {k: prediction.get(k) for k in ("health_score","failure_probability","anomaly_score","rul_cycles","confidence","data_quality","model_mode","model_version","window_ready")},
            "provenance": dict(provenance), "explanation": explanation, "drift": drift, "error": error,
        })

    def metrics(self):
        values = sorted(self.latencies)
        p95 = values[min(len(values)-1, math.ceil(.95*len(values))-1)] if values else 0.0
        return {
            "phase_c_version": PHASE_C_VERSION,
            "predictions_total": self.total,
            "status_counts": dict(self.counts),
            "latency_ms": {"last": round(self.latencies[-1],3) if self.latencies else 0.0, "mean": round(statistics.fmean(self.latencies),3) if self.latencies else 0.0, "p95": round(p95,3)},
            "audit_records_retained": len(self.audit),
            "tracked_aircraft_components": len(self.outputs),
        }

    def audit_records(self, limit=50):
        limit = max(1, min(int(limit), len(self.audit)))
        return list(self.audit)[-limit:]
