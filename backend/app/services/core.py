from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
import random
from pathlib import Path

import numpy as np

from ml.cmapss.runtime import CMapssModelRuntime, RAW_FEATURES
from ml.health import fuse_health

COMPONENTS = ("ENGINE", "HYDRAULIC", "ELECTRICAL", "LANDING_GEAR")


@dataclass
class Aircraft:
    id: str
    status: str
    components: dict[str, dict] = field(default_factory=dict)


class FleetService:
    def __init__(self):
        self.rng = random.Random(26249)
        self.spares_data = [
            {"part_id": "ENG-FLT", "quantity": 9, "lead_time_days": 2},
            {"part_id": "HYD-PMP", "quantity": 4, "lead_time_days": 6},
            {"part_id": "ELEC-REG", "quantity": 6, "lead_time_days": 4},
            {"part_id": "LG-ACT", "quantity": 3, "lead_time_days": 8},
        ]
        self.aircraft = {}
        self.runtime = CMapssModelRuntime(
            os.getenv("FLEETAVAIL_MODEL_DIR", "models/cmapss"),
            rul_architecture=os.getenv("FLEETAVAIL_RUL_MODEL", "lstm").lower(),
        )
        self.latest_predictions: dict[tuple[str, str], dict] = {}
        self.replay_rows: dict[str, list[dict]] = {}
        self.replay_index: dict[str, int] = {}

        for i in range(1, 13):
            comps = {}
            for j, c in enumerate(COMPONENTS):
                h = max(
                    .25,
                    min(.98, .82 - .025 * ((i * (j + 2)) % 7)
                        - (.23 if c == "ENGINE" and i in {3, 7, 11} else 0)),
                )
                comps[c] = {
                    "health": h,
                    "rul": max(8, 180 * h - i * 2),
                    "risk": max(.01, min(.99, 1 - h + (.18 if h < .55 else 0))),
                    "anomaly": 1 - h,
                    "confidence": .83,
                    "data_quality": .98,
                    "model_mode": "synthetic_fallback",
                    "model_version": "HEURISTIC_V1",
                    "window_ready": False,
                }
                self.aircraft[f"AF-{i:03d}"] = Aircraft(
                    f"AF-{i:03d}",
                    ("READY", "READY", "READY", "DEGRADED", "MAINTENANCE")[(i - 1) % 5],
                    comps,
                )

        self._load_cmapss_replay()

    def _load_cmapss_replay(self):
        """Use local C-MAPSS test trajectories as realistic demo telemetry when available."""
        root = Path(os.getenv("FLEETAVAIL_CMAPSS_ROOT", "data/raw/cmapss"))
        try:
            from ml.cmapss.data import load_cmapss
            _, test = load_cmapss(root, "FD001")
            units = sorted(test.unit_id.unique())
            for idx, aid in enumerate(self.aircraft):
                if idx >= len(units):
                    break
                unit = units[idx]
                rows = test[test.unit_id == unit].sort_values("cycle")
                self.replay_rows[aid] = rows.to_dict("records")
                self.replay_index[aid] = 0
                # Warm the 30-cycle runtime window from the actual local dataset.
                self.runtime.seed_history(
                    aid,
                    "ENGINE",
                    self.replay_rows[aid][-self.runtime.window_size:],
                )
                prediction = self.runtime.predict(
                    aid,
                    "ENGINE",
                    self.replay_rows[aid][-1],
                    cycle=int(self.replay_rows[aid][-1]["cycle"]),
                )
                self._apply_prediction(aid, "ENGINE", prediction)
        except Exception:
            # The API remains runnable without the NASA dataset.
            self.replay_rows = {}
            self.replay_index = {}

    def _synthetic_telemetry(self, aid: str, component: str) -> dict:
        """Create a complete C-MAPSS-shaped row for local demo fallback."""
        state = self.aircraft[aid].components[component]
        degradation = 1.0 - state["health"]
        cycle = int(state.get("_cycle", 0)) + 1
        state["_cycle"] = cycle
        row = {
            "op_setting_1": 0.0 + self.rng.gauss(0, .01),
            "op_setting_2": 0.0 + self.rng.gauss(0, .01),
            "op_setting_3": 0.0 + self.rng.gauss(0, .01),
        }
        for i in range(1, 22):
            baseline = 0.0
            if i in {2, 3, 4}:
                baseline = {2: 642.0, 3: 1580.0, 4: 1400.0}[i]
            elif i in {11, 12}:
                baseline = {11: 47.0, 12: 521.0}[i]
            value = baseline * (1 + degradation * .05) if baseline else degradation
            row[f"sensor_{i}"] = value + self.rng.gauss(0, max(abs(value) * .01, .01))
        row["egt_c"] = row["sensor_2"]
        row["vibration_g"] = row["sensor_3"] / 1000.0
        row["oil_pressure_kpa"] = row["sensor_4"] / 3.4
        return row

    def _apply_prediction(self, aid: str, component: str, prediction: dict):
        x = self.aircraft[aid].components[component]
        if prediction.get("rul_cycles") is None:
            return
        x.update({
            "rul": prediction["rul_cycles"],
            "risk": prediction["failure_probability"],
            "anomaly": prediction["anomaly_score"],
            "confidence": prediction["confidence"],
            "data_quality": prediction["data_quality"],
            "model_mode": prediction["model_mode"],
            "model_version": prediction["model_version"],
            "window_ready": prediction["window_ready"],
        })

    def health(self):
        return {
            "status": "healthy",
            "service": "FleetAvail",
            "aircraft_count": len(self.aircraft),
            "mode": self.runtime.mode,
            "models": self.runtime.model_status,
        }

    def fused(self, a: Aircraft, component: str):
        x = a.components[component]
        fused = fuse_health(
            x["health"],
            x["anomaly"],
            x["data_quality"],
            x["risk"],
            x["rul"],
        )
        return {
            "aircraft_id": a.id,
            "component": component,
            **fused,
            "confidence": round(x["confidence"], 4),
            "model_mode": x["model_mode"],
            "model_version": x["model_version"],
            "window_ready": x["window_ready"],
        }

    def fleet_summary(self):
        total = len(self.aircraft)
        ready = sum(a.status == "READY" for a in self.aircraft.values())
        degraded = sum(a.status == "DEGRADED" for a in self.aircraft.values())
        maint = total - ready - degraded
        critical = sum(
            self.fused(a, "ENGINE")["operational_state"] == "CRITICAL"
            for a in self.aircraft.values()
        )
        avail = 100 * ready / total
        return {
            "total_aircraft": total,
            "ready": ready,
            "degraded": degraded,
            "maintenance": maint,
            "critical_aircraft": critical,
            "current_availability_pct": round(avail, 1),
            "projected_7_day_availability_pct": round(max(0, avail - critical * 2.5), 1),
            "ml_mode": self.runtime.mode,
        }

    def aircraft_list(self):
        return [
            {
                "aircraft_id": a.id,
                "status": a.status,
                "engine": self.fused(a, "ENGINE"),
            }
            for a in self.aircraft.values()
        ]

    def aircraft_detail(self, aid):
        if aid not in self.aircraft:
            raise KeyError(aid)
        a = self.aircraft[aid]
        return {
            "aircraft_id": aid,
            "status": a.status,
            "components": {c: self.fused(a, c) for c in COMPONENTS},
        }

    def predict(self, aid, component, telemetry):
        if aid not in self.aircraft:
            raise KeyError(aid)
        if component not in COMPONENTS:
            raise ValueError(f"Unsupported component: {component}")

        if component == "ENGINE":
            prediction = self.runtime.predict(aid, component, telemetry)
            self.latest_predictions[(aid, component)] = prediction
            self._apply_prediction(aid, component, prediction)
            return {
                **self.fused(self.aircraft[aid], component),
                "inference": prediction,
            }

        x = self.aircraft[aid].components[component]
        if telemetry:
            x["health"] = max(.05, min(.99, x["health"] - .02))
            x["anomaly"] = 1 - x["health"]
            x["risk"] = max(.01, min(.99, 1 - x["health"]))
        return self.fused(self.aircraft[aid], component)

    def what_if(self, aid, component, degradation_pct):
        b = self.fused(self.aircraft[aid], component)
        h = max(1, b["health_score"] * (1 - degradation_pct / 100))
        rul = max(1, b["rul_cycles"] * (1 - degradation_pct / 100))
        risk = min(.99, b["failure_probability"] + degradation_pct / 130)
        avail = self.fleet_summary()["current_availability_pct"]
        return {
            "baseline": b,
            "scenario": {
                "degradation_pct": degradation_pct,
                "health_score": round(h, 1),
                "rul_cycles": round(rul, 1),
                "failure_probability": round(risk, 3),
                "projected_fleet_availability_pct": round(
                    max(0, avail - max(0, degradation_pct) * .12), 1
                ),
            },
        }

    def maintenance_recommendation(self, aid, mission):
        a = self.aircraft[aid]
        rows = sorted(
            [
                (
                    self.fused(a, c)["failure_probability"] * .65
                    + (1 / (1 + self.fused(a, c)["rul_cycles"])) * 8,
                    c,
                    self.fused(a, c),
                )
                for c in COMPONENTS
            ],
            reverse=True,
        )
        _, component, prediction = rows[0]
        part = {
            "ENGINE": "ENG-FLT",
            "HYDRAULIC": "HYD-PMP",
            "ELECTRICAL": "ELEC-REG",
            "LANDING_GEAR": "LG-ACT",
        }[component]
        inventory = next(x for x in self.spares_data if x["part_id"] == part)
        action = (
            "SCHEDULE_MAINTENANCE"
            if prediction["failure_probability"] >= .6 or prediction["rul_cycles"] < 45
            else "CONTINUE_MONITORING"
        )
        return {
            "aircraft_id": aid,
            "priority_component": component,
            "recommended_action": action,
            "rul_cycles": prediction["rul_cycles"],
            "failure_probability": prediction["failure_probability"],
            "operational_state": prediction["operational_state"],
            "spare": inventory,
            "reason_codes": [
                "FAILURE_RISK",
                "RUL_URGENCY",
                "MISSION_PRIORITY",
                "SPARE_AVAILABILITY",
            ],
        }

    def spares(self):
        return self.spares_data

    def next_telemetry_event(self):
        aid = self.rng.choice(list(self.aircraft))
        if aid in self.replay_rows and self.replay_rows[aid]:
            rows = self.replay_rows[aid]
            idx = self.replay_index[aid] % len(rows)
            telemetry = rows[idx].copy()
            self.replay_index[aid] = idx + 1
        else:
            telemetry = self._synthetic_telemetry(aid, "ENGINE")

        prediction = self.predict(aid, "ENGINE", telemetry)
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "telemetry_update",
            "aircraft_id": aid,
            "component": "ENGINE",
            "telemetry": {
                k: float(v) for k, v in telemetry.items()
                if k in RAW_FEATURES
            },
            "prediction": prediction,
        }
        return result
