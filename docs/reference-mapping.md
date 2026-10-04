# Reference-to-FleetAvail Mapping

| Reference | Pattern used |
|---|---|
| AeroSentinal | Whole-aircraft subsystem boundaries, fusion, what-if simulation, edge-ready model contracts, aircraft dashboard concept |
| Dattateja | ETL/training/inference separation, hybrid XGBoost + LSTM target, batch/stream interfaces, fleet state |
| DRDO-UAV-EngineTwin | Digital-twin state, sensor-fusion mindset, fault/degradation injection and telemetry boundary |
| Ocramnaig94 | Diagnose -> prognose -> maintenance workflow |
| Saroswat | Engine-grouped/time-aware validation, causal features, uncertainty and cost-aware decisions |
| Karthikeyan | Clean RUL model/API/dashboard progression |

FleetAvail uses these as architectural references. It does not copy their source trees wholesale. The current implementation uses original interfaces and a deterministic demo provider so the system runs before real model artifacts are installed.

Replacement boundaries:
- ml/model_contract.py: XGBoost failure-risk, LSTM/TCN/Transformer RUL and anomaly providers
- digital_twin/state.py: richer physics-informed twin
- decision_engine/maintenance.py: OR-Tools scheduling and spare allocation
