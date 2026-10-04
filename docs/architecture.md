# FleetAvail Architecture

Telemetry + maintenance records → validation/features → anomaly + failure-risk + RUL → health fusion → digital twin → maintenance/spares → fleet availability → dashboard.

Reference patterns: AeroSentinal (subsystem PHM, fusion, simulator, 3D-ready frontend); Dattateja (ETL, hybrid XGBoost/LSTM, streaming and fleet APIs); DRDO-UAV-EngineTwin (digital-twin state, sensor fusion and fault injection); Ocramnaig94 (digital-twin maintenance lifecycle); Saroswat (engine-grouped validation, causal features, cost-aware decisions); Karthikeyan (deployable model/API/dashboard progression).

This first commit is an original integration scaffold. It deliberately uses synthetic telemetry so the system is runnable without proprietary aircraft data or external model weights.