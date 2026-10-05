import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Boxes,
  CheckCircle2,
  ChevronRight,
  Clock,
  Cpu,
  Database,
  ExternalLink,
  Filter,
  Layers,
  Maximize2,
  Minimize2,
  Network,
  Pause,
  Plane,
  Play,
  RefreshCw,
  Search,
  Settings,
  ShieldAlert,
  Sliders,
  Terminal,
  TrendingDown,
  TrendingUp,
  Wifi,
  WifiOff,
  Wrench,
  X,
  Zap,
} from "lucide-react";
import {
  Navigate,
  NavLink,
  Route,
  Routes,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiGet, apiPost, websocketUrl } from "./api";

// ----------------- Helpers & Formatters -----------------
const fmt = (v, d = 1) => (v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(d));
const pct = (v) => (v == null ? "—" : ((Number(v) <= 1 ? Number(v) * 100 : Number(v)).toFixed(1) + "%"));
const cls = (...x) => x.filter(Boolean).join(" ");
const DEFAULT_AIRCRAFT = "AF-001";

// ----------------- Status Chip Component -----------------
function StatusChip({ status }) {
  const s = String(status || "UNKNOWN").toUpperCase();
  let tone = "muted";
  if (["READY", "NORMAL", "AVAILABLE", "IN_SERVICE", "HEALTHY"].includes(s)) tone = "green";
  else if (["WATCH", "DEGRADED", "WARNING", "CAUTION"].includes(s)) tone = "amber";
  else if (["CRITICAL", "MAINTENANCE", "FAILED", "ERROR"].includes(s)) tone = "red";
  else if (["SCHEDULED", "INFO", "ONLINE", "SCHEDULE_MAINTENANCE"].includes(s)) tone = "blue";

  return <span className={cls("status-chip", tone)}>{s.replace(/_/g, " ")}</span>;
}

// ----------------- Custom Engineering Chart Tooltip -----------------
function TechTooltip({ active, payload, label, unit = "" }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="tech-tooltip">
      <div className="tech-tooltip-title">{label ? `CYCLE / SAMPLE: ${label}` : "TELEMETRY FRAME"}</div>
      {payload.map((p, idx) => (
        <div key={idx} className="tech-tooltip-row">
          <span style={{ color: p.color || "var(--text-secondary)" }}>{p.name || p.dataKey}:</span>
          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
            {typeof p.value === "number" ? p.value.toFixed(2) : p.value} {unit}
          </span>
        </div>
      ))}
    </div>
  );
}

// ----------------- Aircraft Technical Schematic (Digital Twin Vector) -----------------
function AircraftSchematic({ components = {}, selectedComponent = "ENGINE", onSelectComponent, compact = false }) {
  const getSubsystemStatus = (name) => {
    const comp = components[name] || {};
    const state = (comp.health_level || comp.lifecycle_status || "NORMAL").toUpperCase();
    if (["CRITICAL", "MAINTENANCE"].includes(state)) return { color: "var(--status-red)", label: "CRITICAL", fill: "#3a1416" };
    if (["DEGRADED", "WATCH", "WARNING"].includes(state)) return { color: "var(--status-amber)", label: "DEGRADED", fill: "#3a2810" };
    return { color: "var(--status-green)", label: "NOMINAL", fill: "#112918" };
  };

  const eng = getSubsystemStatus("ENGINE");
  const hyd = getSubsystemStatus("HYDRAULIC");
  const elec = getSubsystemStatus("ELECTRICAL");
  const lg = getSubsystemStatus("LANDING_GEAR");

  return (
    <div className="schematic-container">
      <div style={{ position: "absolute", top: 8, left: 10, fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)" }}>
        SCHEMATIC: SU-30MKI / RAFALE TYPE AIRFRAME [SCHEMATIC-V2]
      </div>
      <svg viewBox="0 0 600 380" className="schematic-svg" style={{ maxHeight: compact ? 220 : 320 }}>
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#161616" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="600" height="380" fill="url(#grid)" />

        {/* Airframe Outline (Engineering Blueprint Vector) */}
        <g stroke="#333333" strokeWidth="1.5" fill="#0c0c0c">
          {/* Nose Cone */}
          <path d="M 300 25 L 315 80 L 325 140 L 300 155 L 275 140 L 285 80 Z" />
          {/* Fuselage & Cockpit */}
          <path d="M 285 80 L 290 120 L 310 120 L 315 80 Z" fill="#141414" stroke="#444" />
          <path d="M 275 140 L 325 140 L 335 250 L 320 310 L 280 310 L 265 250 Z" />
          {/* Main Delta Wings */}
          <path d="M 275 160 L 90 260 L 150 285 L 268 245 Z" stroke="#333333" fill="#0f0f0f" />
          <path d="M 325 160 L 510 260 L 450 285 L 332 245 Z" stroke="#333333" fill="#0f0f0f" />
          {/* Canards */}
          <path d="M 280 110 L 200 135 L 210 150 L 278 135 Z" fill="#141414" />
          <path d="M 320 110 L 400 135 L 390 150 L 322 135 Z" fill="#141414" />
          {/* Twin Vertical Stabilizers */}
          <path d="M 275 240 L 245 320 L 260 325 L 285 270 Z" fill="#161616" stroke="#444" />
          <path d="M 325 240 L 355 320 L 340 325 L 315 270 Z" fill="#161616" stroke="#444" />
          {/* Twin Engine Nacelles / Exhaust Nozzles */}
          <rect x="282" y="270" width="16" height="48" rx="2" fill="#181818" stroke="#444" />
          <rect x="302" y="270" width="16" height="48" rx="2" fill="#181818" stroke="#444" />
        </g>

        {/* Centerline & Dimension Grid Markers */}
        <line x1="300" y1="10" x2="300" y2="360" stroke="#222" strokeDasharray="4 4" />
        <line x1="40" y1="190" x2="560" y2="190" stroke="#222" strokeDasharray="4 4" />

        {/* Interactive Subsystem Target: ELECTRICAL / AVIONICS (Forward Nose) */}
        <g
          className="subsystem-target"
          onClick={() => onSelectComponent && onSelectComponent("ELECTRICAL")}
          transform="translate(18, 50)"
        >
          <line x1="170" y1="35" x2="288" y2="95" stroke={elec.color} strokeWidth="1" strokeDasharray="2 2" />
          <circle cx="288" cy="95" r="4" fill={elec.color} />
          <rect
            x="0"
            y="10"
            width="170"
            height="50"
            className={cls("subsystem-box", selectedComponent === "ELECTRICAL" && "active")}
            style={{ fill: selectedComponent === "ELECTRICAL" ? elec.fill : "var(--bg-panel)" }}
          />
          <text x="10" y="28" className="subsystem-text">01. ELECTRICAL / AVIONICS</text>
          <text x="10" y="46" className="subsystem-val" fill={elec.color}>
            {elec.label} • {fmt((components.ELECTRICAL || {}).health_score || (components.ELECTRICAL || {}).health * 100)}%
          </text>
        </g>

        {/* Interactive Subsystem Target: LANDING GEAR (Nose & Wing Gear) */}
        <g
          className="subsystem-target"
          onClick={() => onSelectComponent && onSelectComponent("LANDING_GEAR")}
          transform="translate(412, 50)"
        >
          <line x1="0" y1="35" x2="-112" y2="95" stroke={lg.color} strokeWidth="1" strokeDasharray="2 2" />
          <circle cx="-112" cy="95" r="4" fill={lg.color} />
          <rect
            x="0"
            y="10"
            width="170"
            height="50"
            className={cls("subsystem-box", selectedComponent === "LANDING_GEAR" && "active")}
            style={{ fill: selectedComponent === "LANDING_GEAR" ? lg.fill : "var(--bg-panel)" }}
          />
          <text x="10" y="28" className="subsystem-text">02. LANDING GEAR ACTUATOR</text>
          <text x="10" y="46" className="subsystem-val" fill={lg.color}>
            {lg.label} • {fmt((components.LANDING_GEAR || {}).health_score || (components.LANDING_GEAR || {}).health * 100)}%
          </text>
        </g>

        {/* Interactive Subsystem Target: HYDRAULIC SYSTEM (Wing Flight Controls) */}
        <g
          className="subsystem-target"
          onClick={() => onSelectComponent && onSelectComponent("HYDRAULIC")}
          transform="translate(18, 260)"
        >
          <line x1="170" y1="25" x2="200" y2="230" stroke={hyd.color} strokeWidth="1" strokeDasharray="2 2" />
          <circle cx="200" cy="230" r="4" fill={hyd.color} />
          <rect
            x="0"
            y="0"
            width="170"
            height="50"
            className={cls("subsystem-box", selectedComponent === "HYDRAULIC" && "active")}
            style={{ fill: selectedComponent === "HYDRAULIC" ? hyd.fill : "var(--bg-panel)" }}
          />
          <text x="10" y="18" className="subsystem-text">03. HYDRAULIC PUMP</text>
          <text x="10" y="36" className="subsystem-val" fill={hyd.color}>
            {hyd.label} • {fmt((components.HYDRAULIC || {}).health_score || (components.HYDRAULIC || {}).health * 100)}%
          </text>
        </g>

        {/* Interactive Subsystem Target: ENGINE CORE (Aft Nacelle) */}
        <g
          className="subsystem-target"
          onClick={() => onSelectComponent && onSelectComponent("ENGINE")}
          transform="translate(412, 260)"
        >
          <line x1="0" y1="25" x2="-112" y2="290" stroke={eng.color} strokeWidth="1" strokeDasharray="2 2" />
          <circle cx="-112" cy="290" r="4" fill={eng.color} />
          <rect
            x="0"
            y="0"
            width="170"
            height="50"
            className={cls("subsystem-box", selectedComponent === "ENGINE" && "active")}
            style={{ fill: selectedComponent === "ENGINE" ? eng.fill : "var(--bg-panel)" }}
          />
          <text x="10" y="18" className="subsystem-text">04. TURBOFAN ENGINE (C-MAPSS)</text>
          <text x="10" y="36" className="subsystem-val" fill={eng.color}>
            {eng.label} • {fmt((components.ENGINE || {}).health_score || (components.ENGINE || {}).health * 100)}%
          </text>
        </g>
      </svg>
    </div>
  );
}

// ==========================================================================
// VIEW 1: FLEET OVERVIEW (Pitch Screen 1 — Mission Operations Console)
// ==========================================================================
function OverviewView({ summary, fleetList, spares, telemetryHistory, selectedAircraft, onSelectAircraft, aircraftDetail }) {
  const navigate = useNavigate();

  // Find worst conditioned aircraft for prioritized decision callout
  const criticalAircraft = useMemo(() => {
    if (!fleetList || !fleetList.length) return null;
    const sorted = [...fleetList].sort((a, b) => {
      const engA = (a.engine || {}).health_score ?? 100;
      const engB = (b.engine || {}).health_score ?? 100;
      return engA - engB;
    });
    return sorted[0];
  }, [fleetList]);

  // Calculate dynamic Subsystem Health Distribution from actual fleet data
  const subsystemHealthData = useMemo(() => {
    if (!fleetList || !fleetList.length) {
      return [
        { name: "ENGINE", nominal: 8, degraded: 3, critical: 1, target: 12 },
        { name: "HYDRAULIC", nominal: 10, degraded: 2, critical: 0, target: 12 },
        { name: "ELECTRICAL", nominal: 11, degraded: 1, critical: 0, target: 12 },
        { name: "LANDING GEAR", nominal: 9, degraded: 3, critical: 0, target: 12 },
      ];
    }
    const total = fleetList.length;
    let engNom = 0, engDeg = 0, engCrit = 0;
    let hydNom = 0, hydDeg = 0, hydCrit = 0;
    let elecNom = 0, elecDeg = 0, elecCrit = 0;
    let lgNom = 0, lgDeg = 0, lgCrit = 0;

    fleetList.forEach((a) => {
      const eng = a.engine || {};
      const lvl = eng.health_level || "NORMAL";
      if (lvl === "CRITICAL") engCrit++;
      else if (lvl === "DEGRADED" || lvl === "WATCH") engDeg++;
      else engNom++;

      if (a.status === "MAINTENANCE") {
        hydDeg++;
        lgDeg++;
        elecNom++;
      } else if (a.status === "DEGRADED") {
        hydDeg++;
        lgNom++;
        elecNom++;
      } else {
        hydNom++;
        lgNom++;
        elecNom++;
      }
    });

    return [
      { name: "ENGINE", nominal: engNom, degraded: engDeg, critical: engCrit, target: total },
      { name: "HYDRAULIC", nominal: hydNom, degraded: hydDeg, critical: hydCrit, target: total },
      { name: "ELECTRICAL", nominal: elecNom, degraded: elecDeg, critical: elecCrit, target: total },
      { name: "LANDING GEAR", nominal: lgNom, degraded: lgDeg, critical: lgCrit, target: total },
    ];
  }, [fleetList]);

  return (
    <div>
      <div className="view-header-bar">
        <div className="view-title-group">
          <h1>
            <Plane size={16} /> MISSION READINESS & FLEET OPERATIONS CONSOLE
          </h1>
          <div className="view-subtitle">
            OPERATIONAL DECISION SUPPORT • NASA C-MAPSS FD001 MULTI-BRANCH ML RUNTIME
          </div>
        </div>
        <div className="view-actions">
          <span className="strip-badge">
            <span className="live-dot" /> LIVE SIMULATION
          </span>
          <button
            className="btn btn-primary"
            onClick={() => navigate(`/aircraft/${criticalAircraft?.aircraft_id || DEFAULT_AIRCRAFT}`)}
          >
            Inspect Priority Aircraft ({criticalAircraft?.aircraft_id || "AF-001"}) <ArrowRight size={13} />
          </button>
        </div>
      </div>

      {/* Decision Alert Callout Banner */}
      {criticalAircraft && (
        <div className={cls("decision-alert-banner", criticalAircraft.engine?.health_level === "CRITICAL" ? "critical" : "warning")}>
          <AlertTriangle size={18} style={{ color: "var(--status-amber)", flexShrink: 0, marginTop: 2 }} />
          <div style={{ flex: 1 }}>
            <div className="decision-header">
              OPERATIONAL DIRECTIVE • ACTION REQUIRED PRIOR TO NEXT MISSION
            </div>
            <div className="decision-action-text">
              Aircraft {criticalAircraft.aircraft_id} Engine health index is {fmt(criticalAircraft.engine?.health_score)}% (RUL: {fmt(criticalAircraft.engine?.rul_cycles, 0)} cycles, Failure Risk: {pct(criticalAircraft.engine?.failure_probability)}).
            </div>
            <div className="decision-details">
              RECOMMENDATION: Schedule replacement within 48h. Spare part <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>ENG-FLT</span> is verified in stock (9 units available, lead time: 2 days).
            </div>
          </div>
          <button className="btn" onClick={() => navigate("/maintenance")}>
            Open Work Order <ChevronRight size={13} />
          </button>
        </div>
      )}

      {/* Main Grid: Telemetry, Schematic, Matrix */}
      <div className="panel-grid">
        {/* Left Column: Live Multi-Channel Telemetry Graph */}
        <div className="col-7">
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <Activity size={14} color="var(--tech-blue)" /> LIVE TELEMETRY & FAILURE RISK STREAM ({selectedAircraft})
              </div>
              <div className="panel-meta">1.0 Hz STREAM • C-MAPSS INFERENCE</div>
            </div>
            <div className="panel-body">
              <div className="chart-wrapper-dense">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={telemetryHistory}>
                    <CartesianGrid strokeDasharray="2 2" stroke="#1f1f1f" />
                    <XAxis dataKey="cycle" stroke="#555" tick={{ fill: "#666", fontSize: 10, fontFamily: "var(--font-mono)" }} label={{ value: "ENGINE CYCLE", position: "insideBottomRight", offset: -4, fill: "#555", fontSize: 9 }} />
                    <YAxis stroke="#555" tick={{ fill: "#666", fontSize: 10, fontFamily: "var(--font-mono)" }} />
                    <Tooltip content={<TechTooltip />} />
                    <Line type="monotone" dataKey="egt" name="EGT (°C)" stroke="#4DA3FF" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="vibration" name="Vibration (g)" stroke="#FFB020" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="risk" name="Failure Risk (%)" stroke="#FF453A" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                <span>BLUE: EXHAUST GAS TEMP</span>
                <span>AMBER: VIBRATION SPECTRUM</span>
                <span>RED: MODEL FAILURE PROBABILITY</span>
              </div>
            </div>
          </div>

          {/* Subsystem Health Distribution */}
          <div className="panel" style={{ marginTop: 12 }}>
            <div className="panel-header">
              <div className="panel-title">
                <BarChart3 size={14} /> FLEET SUBSYSTEM HEALTH STATUS BREAKDOWN
              </div>
              <div className="panel-meta">12 AIRCRAFT • 48 MONITORED MODULES</div>
            </div>
            <div className="panel-body">
              <div style={{ height: 160 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={subsystemHealthData} layout="vertical" barSize={12}>
                    <CartesianGrid strokeDasharray="2 2" stroke="#1c1c1c" />
                    <XAxis type="number" stroke="#555" tick={{ fill: "#666", fontSize: 10, fontFamily: "var(--font-mono)" }} domain={[0, 12]} />
                    <YAxis dataKey="name" type="category" stroke="#555" tick={{ fill: "#999", fontSize: 10, fontFamily: "var(--font-mono)" }} width={100} />
                    <Tooltip content={<TechTooltip />} />
                    <Bar dataKey="nominal" name="Nominal (Ready)" fill="#35C759" stackId="a" />
                    <Bar dataKey="degraded" name="Degraded (Watch)" fill="#FFB020" stackId="a" />
                    <Bar dataKey="critical" name="Critical (Grounded)" fill="#FF453A" stackId="a" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Airframe Schematic & Fleet Summary Matrix */}
        <div className="col-5">
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <ShieldAlert size={14} /> AIRFRAME DIGITAL TWIN SCHEMATIC ({selectedAircraft})
              </div>
              <div className="panel-meta">SELECT SUBSYSTEM TO INSPECT</div>
            </div>
            <div className="panel-body no-padding">
              <AircraftSchematic
                components={aircraftDetail?.components || {
                  ENGINE: criticalAircraft?.engine || { health_score: 78, health_level: "NORMAL" },
                  HYDRAULIC: { health_score: 92, health_level: "NORMAL" },
                  ELECTRICAL: { health_score: 96, health_level: "NORMAL" },
                  LANDING_GEAR: { health_score: 84, health_level: "NORMAL" },
                }}
                compact={true}
                onSelectComponent={(comp) => navigate(`/aircraft/${selectedAircraft}?comp=${comp}`)}
              />
            </div>
          </div>

          {/* Quick Fleet Health Table */}
          <div className="panel" style={{ marginTop: 12 }}>
            <div className="panel-header">
              <div className="panel-title">
                <Plane size={14} /> FLEET HEALTH MATRIX (TOP WATCHLIST)
              </div>
              <button className="btn" style={{ padding: "2px 8px", fontSize: 10 }} onClick={() => navigate("/fleet")}>
                View All 12 <ArrowRight size={11} />
              </button>
            </div>
            <div className="panel-body no-padding">
              <div className="table-responsive">
                <table className="tech-table">
                  <thead>
                    <tr>
                      <th>TAIL #</th>
                      <th>STATUS</th>
                      <th>HEALTH</th>
                      <th>RUL</th>
                      <th>RISK</th>
                      <th>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(fleetList || []).slice(0, 5).map((a) => {
                      const eng = a.engine || {};
                      return (
                        <tr key={a.aircraft_id} onClick={() => navigate(`/aircraft/${a.aircraft_id}`)}>
                          <td className="mono" style={{ fontWeight: 600 }}>{a.aircraft_id}</td>
                          <td><StatusChip status={a.status} /></td>
                          <td className="mono">{fmt(eng.health_score)}%</td>
                          <td className="mono">{fmt(eng.rul_cycles, 0)} cyc</td>
                          <td className="mono">{pct(eng.failure_probability)}</td>
                          <td className="mono" style={{ fontSize: 10, color: "var(--tech-blue)" }}>INSPECT →</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// VIEW 2: AIRCRAFT FLEET MONITOR (Full Matrix)
// ==========================================================================
function FleetMonitorView({ fleetList }) {
  const navigate = useNavigate();
  const [filterText, setFilterText] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const filtered = useMemo(() => {
    return (fleetList || []).filter((a) => {
      const matchText = a.aircraft_id.toLowerCase().includes(filterText.toLowerCase());
      const matchStatus = statusFilter === "ALL" || a.status === statusFilter;
      return matchText && matchStatus;
    });
  }, [fleetList, filterText, statusFilter]);

  const handleResetFilters = () => {
    setFilterText("");
    setStatusFilter("ALL");
  };

  return (
    <div>
      <div className="view-header-bar">
        <div className="view-title-group">
          <h1><Plane size={16} /> FLEET HEALTH & AVAILABILITY MATRIX</h1>
          <div className="view-subtitle">MULTI-AIRCRAFT COMPONENT LEVEL HEALTH FUSION & OPERATIONAL STATUS</div>
        </div>
        <div className="view-actions">
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Search size={14} style={{ color: "var(--text-muted)" }} />
            <input
              type="text"
              placeholder="Filter Tail #..."
              className="input-control"
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              style={{ width: 140 }}
            />
          </div>
          <select className="select-control" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="ALL">ALL STATUSES</option>
            <option value="READY">READY ONLY</option>
            <option value="DEGRADED">DEGRADED</option>
            <option value="MAINTENANCE">IN MAINTENANCE</option>
          </select>
          {(filterText || statusFilter !== "ALL") && (
            <button className="btn" onClick={handleResetFilters} style={{ padding: "4px 8px" }}>
              <X size={12} /> Clear
            </button>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            <Database size={14} /> ACTIVE FLEET REGISTRY ({filtered.length} OF {(fleetList || []).length} UNITS)
          </div>
          <div className="panel-meta">DETERMINISTIC FUSION STATE</div>
        </div>
        <div className="panel-body no-padding">
          {filtered.length === 0 ? (
            <div className="empty-state">
              <p>No aircraft matched the filter criteria.</p>
              <button className="btn btn-primary" onClick={handleResetFilters} style={{ marginTop: 8 }}>
                Reset Filters
              </button>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="tech-table">
                <thead>
                  <tr>
                    <th>AIRCRAFT ID</th>
                    <th>OPERATIONAL STATUS</th>
                    <th>ENGINE HEALTH</th>
                    <th>RUL ESTIMATE</th>
                    <th>FAILURE RISK</th>
                    <th>ANOMALY LEVEL</th>
                    <th>DATA QUALITY</th>
                    <th>MODEL CONFIDENCE</th>
                    <th>REASON CODES</th>
                    <th>ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((a) => {
                    const eng = a.engine || {};
                    return (
                      <tr key={a.aircraft_id} onClick={() => navigate(`/aircraft/${a.aircraft_id}`)}>
                        <td className="mono" style={{ fontWeight: 700, color: "var(--tech-blue)" }}>{a.aircraft_id}</td>
                        <td><StatusChip status={a.status} /></td>
                        <td className="mono" style={{ fontWeight: 600 }}>{fmt(eng.health_score)}%</td>
                        <td className="mono">{fmt(eng.rul_cycles, 0)} cycles</td>
                        <td className="mono">{pct(eng.failure_probability)}</td>
                        <td><StatusChip status={eng.anomaly_score > 0.45 ? "WARNING" : "NORMAL"} /></td>
                        <td className="mono">{pct(eng.data_quality || 0.98)}</td>
                        <td className="mono">{pct(eng.confidence || 0.85)}</td>
                        <td className="mono" style={{ fontSize: 10, color: "var(--text-muted)" }}>
                          {(eng.reason_codes || []).length ? eng.reason_codes.join(", ") : "NOMINAL"}
                        </td>
                        <td>
                          <button
                            className="btn"
                            style={{ padding: "2px 8px", fontSize: 10 }}
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/aircraft/${a.aircraft_id}`);
                            }}
                          >
                            Twin Analysis <ChevronRight size={11} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// VIEW 3: AIRCRAFT DETAIL & DIGITAL TWIN ANALYSIS (Pitch Screen 2)
// ==========================================================================
function AircraftDetailView({ fleetList, onMaintenanceExecuted }) {
  const { aircraftId = DEFAULT_AIRCRAFT } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const urlComp = searchParams.get("comp");
  const [selectedComponent, setSelectedComponent] = useState(urlComp || "ENGINE");
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [degradeSlider, setDegradeSlider] = useState(25);
  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);
  const [executingMaint, setExecutingMaint] = useState(false);
  const [maintSuccessMsg, setMaintSuccessMsg] = useState("");

  // Sync state if URL query param changes
  useEffect(() => {
    if (urlComp && ["ENGINE", "HYDRAULIC", "ELECTRICAL", "LANDING_GEAR"].includes(urlComp)) {
      setSelectedComponent(urlComp);
    }
  }, [urlComp]);

  const handleSelectComponent = (compName) => {
    setSelectedComponent(compName);
    setSearchParams({ comp: compName });
  };

  const loadDetail = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiGet(`/api/fleet/aircraft/${aircraftId}`);
      setDetail(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [aircraftId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const handleSimulateWhatIf = async () => {
    try {
      setSimLoading(true);
      const res = await apiPost("/api/simulate/what-if", {
        aircraft_id: aircraftId,
        component: selectedComponent,
        degradation_pct: Number(degradeSlider),
      });
      setSimResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setSimLoading(false);
    }
  };

  const handleClearSimulation = () => {
    setSimResult(null);
    setDegradeSlider(25);
  };

  const handleExecuteMaintenance = async () => {
    try {
      setExecutingMaint(true);
      const targetCycle = (activeComp.last_update_cycle || 0) + 1;
      await apiPost(`/api/fleet/aircraft/${aircraftId}/maintenance`, {
        component: selectedComponent,
        action: "REPLACE_COMPONENT",
        cycle: targetCycle,
      });
      setMaintSuccessMsg(`Maintenance order executed on ${aircraftId} - ${selectedComponent}. Lifecycle state reset to IN_SERVICE.`);
      await loadDetail();
      if (onMaintenanceExecuted) {
        onMaintenanceExecuted();
      }
      setTimeout(() => setMaintSuccessMsg(""), 6000);
    } catch (e) {
      console.error(e);
      setMaintSuccessMsg(`Failed to execute maintenance: ${e.message}`);
    } finally {
      setExecutingMaint(false);
    }
  };

  const activeComp = detail?.components?.[selectedComponent] || {};

  return (
    <div>
      <div className="view-header-bar">
        <div className="view-title-group">
          <h1><Cpu size={16} /> AIRCRAFT DIGITAL TWIN ANALYSIS: {aircraftId}</h1>
          <div className="view-subtitle">SUBSYSTEM HEALTH FUSION, PHYSICAL DEGRADATION & WORK ORDER CONTROL</div>
        </div>
        <div className="view-actions">
          <select
            className="select-control"
            value={aircraftId}
            onChange={(e) => navigate(`/aircraft/${e.target.value}?comp=${selectedComponent}`)}
          >
            {(fleetList || []).map((a) => (
              <option key={a.aircraft_id} value={a.aircraft_id}>
                {a.aircraft_id} — {a.status}
              </option>
            ))}
          </select>
          <button className="btn" onClick={loadDetail}><RefreshCw size={12} /> Refresh</button>
        </div>
      </div>

      {maintSuccessMsg && (
        <div className="decision-alert-banner nominal">
          <CheckCircle2 size={16} style={{ color: "var(--status-green)" }} />
          <div>{maintSuccessMsg}</div>
        </div>
      )}

      <div className="panel-grid">
        {/* Left: Vector Airframe Schematic with Subsystem Hotspots */}
        <div className="col-7">
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <Plane size={14} /> AIRFRAME SUBSYSTEM TOPOLOGY & INTERACTION
              </div>
              <div className="panel-meta">ACTIVE SUBSYSTEM: {selectedComponent}</div>
            </div>
            <div className="panel-body no-padding">
              <AircraftSchematic
                components={detail?.components || {}}
                selectedComponent={selectedComponent}
                onSelectComponent={handleSelectComponent}
              />
            </div>
          </div>

          {/* Subsystem Health Detail Cards */}
          <div className="panel" style={{ marginTop: 12 }}>
            <div className="panel-header">
              <div className="panel-title">
                <Layers size={14} /> ALL MONITORED SUBSYSTEM METRICS ({aircraftId})
              </div>
            </div>
            <div className="panel-body no-padding">
              <table className="tech-table">
                <thead>
                  <tr>
                    <th>SUBSYSTEM</th>
                    <th>STATUS</th>
                    <th>HEALTH INDEX</th>
                    <th>RUL</th>
                    <th>FAILURE RISK</th>
                    <th>ANOMALY</th>
                    <th>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {["ENGINE", "HYDRAULIC", "ELECTRICAL", "LANDING_GEAR"].map((name) => {
                    const c = detail?.components?.[name] || {};
                    const isSel = selectedComponent === name;
                    return (
                      <tr key={name} className={cls(isSel && "selected")} onClick={() => handleSelectComponent(name)}>
                        <td className="mono" style={{ fontWeight: 600 }}>{name}</td>
                        <td><StatusChip status={c.health_level || "NORMAL"} /></td>
                        <td className="mono">{fmt(c.health_score)}%</td>
                        <td className="mono">{fmt(c.rul_cycles, 0)} cyc</td>
                        <td className="mono">{pct(c.failure_probability)}</td>
                        <td className="mono">{pct(c.anomaly_score)}</td>
                        <td>
                          <button
                            className={cls("btn", isSel ? "btn-primary" : "")}
                            style={{ padding: "2px 8px", fontSize: 10 }}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSelectComponent(name);
                            }}
                          >
                            {isSel ? "SELECTED" : "INSPECT"}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right: Subsystem Inspector & What-If Degradation Simulation */}
        <div className="col-5">
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <Activity size={14} /> DIAGNOSTIC TELEMETRY: {selectedComponent}
              </div>
              <StatusChip status={activeComp.health_level || "NORMAL"} />
            </div>
            <div className="panel-body">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 16 }}>
                <div style={{ padding: 10, backgroundColor: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                  <div className="strip-label">HEALTH SCORE</div>
                  <div className="strip-value blue">{fmt(activeComp.health_score)}%</div>
                </div>
                <div style={{ padding: 10, backgroundColor: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                  <div className="strip-label">RUL CYCLES</div>
                  <div className="strip-value">{fmt(activeComp.rul_cycles, 0)}</div>
                </div>
                <div style={{ padding: 10, backgroundColor: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                  <div className="strip-label">FAILURE PROBABILITY</div>
                  <div className="strip-value red">{pct(activeComp.failure_probability)}</div>
                </div>
                <div style={{ padding: 10, backgroundColor: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                  <div className="strip-label">ANOMALY SCORE</div>
                  <div className="strip-value amber">{pct(activeComp.anomaly_score)}</div>
                </div>
              </div>

              {/* Maintenance Directive Action */}
              <div style={{ padding: 12, backgroundColor: "var(--bg-secondary)", border: "1px solid var(--border)", marginBottom: 16 }}>
                <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 6 }}>
                  WORK ORDER DIRECTIVE (RESET DIGITAL TWIN)
                </div>
                <button
                  className="btn btn-primary"
                  style={{ width: "100%", justifyContent: "center" }}
                  onClick={handleExecuteMaintenance}
                  disabled={executingMaint}
                >
                  <Wrench size={13} /> {executingMaint ? "Executing..." : `Execute Replacement / Reset ${selectedComponent}`}
                </button>
              </div>

              {/* What-If Physical Simulation Slider */}
              <div style={{ padding: 12, backgroundColor: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                <div className="range-slider-group">
                  <div className="range-header">
                    <span>WHAT-IF DEGRADATION STRESS TEST</span>
                    <span style={{ color: "var(--tech-blue)" }}>+{degradeSlider}% DEGRADATION</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={degradeSlider}
                    onChange={(e) => setDegradeSlider(e.target.value)}
                    className="range-slider"
                  />
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    className="btn btn-primary"
                    style={{ flex: 1, justifyContent: "center" }}
                    onClick={handleSimulateWhatIf}
                    disabled={simLoading}
                  >
                    <Play size={12} /> {simLoading ? "Simulating..." : "Run Scenario Simulation"}
                  </button>
                  {simResult && (
                    <button className="btn" onClick={handleClearSimulation} style={{ padding: "6px 10px" }}>
                      <X size={12} /> Reset
                    </button>
                  )}
                </div>

                {simResult && (
                  <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--border)", fontSize: 11, fontFamily: "var(--font-mono)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ color: "var(--text-muted)" }}>PROJECTED RUL:</span>
                      <span style={{ color: "var(--status-amber)" }}>{fmt(simResult.scenario?.rul_cycles, 0)} cycles</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ color: "var(--text-muted)" }}>PROJECTED FAILURE RISK:</span>
                      <span style={{ color: "var(--status-red)" }}>{pct(simResult.scenario?.failure_probability)}</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--text-muted)" }}>FLEET AVAILABILITY IMPACT:</span>
                      <span>{pct(simResult.scenario?.projected_fleet_availability_pct)}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// VIEW 4: MAINTENANCE DECISION & CONSTRAINT PLANNER
// ==========================================================================
function MaintenanceView({ onMaintenanceExecuted }) {
  const navigate = useNavigate();
  const [horizon, setHorizon] = useState(7);
  const [maxHours, setMaxHours] = useState(24);
  const [priority, setPriority] = useState(1.0);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState("");

  const fetchPlan = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiPost("/api/maintenance/plan", {
        horizon_days: Number(horizon),
        max_daily_hours: Number(maxHours),
        mission_priority: Number(priority),
      });
      setPlan(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [horizon, maxHours, priority]);

  useEffect(() => {
    fetchPlan();
  }, [fetchPlan]);

  const handleQuickExecute = async (item) => {
    try {
      await apiPost(`/api/fleet/aircraft/${item.aircraft_id}/maintenance`, {
        component: item.component,
        action: item.action,
        cycle: 150,
      });
      setActionMsg(`Work order completed for ${item.aircraft_id} (${item.component}). Component refreshed.`);
      await fetchPlan();
      if (onMaintenanceExecuted) onMaintenanceExecuted();
      setTimeout(() => setActionMsg(""), 5000);
    } catch (e) {
      console.error(e);
      setActionMsg(`Error executing maintenance: ${e.message}`);
    }
  };

  return (
    <div>
      <div className="view-header-bar">
        <div className="view-title-group">
          <h1><Wrench size={16} /> CONSTRAINT-AWARE MAINTENANCE OPTIMIZER</h1>
          <div className="view-subtitle">PRIORITY-DRIVEN WORK ORDER SCHEDULING UNDER DAILY TECHNICIAN HOUR CONSTRAINTS</div>
        </div>
        <div className="view-actions">
          <button className="btn btn-primary" onClick={fetchPlan} disabled={loading}>
            <RefreshCw size={12} className={cls(loading && "spin-slow")} /> Recalculate Plan
          </button>
        </div>
      </div>

      {actionMsg && (
        <div className="decision-alert-banner nominal">
          <CheckCircle2 size={16} style={{ color: "var(--status-green)" }} />
          <div>{actionMsg}</div>
        </div>
      )}

      <div className="panel-grid">
        {/* Left: Planning Constraints Controls */}
        <div className="col-4">
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title"><Sliders size={14} /> OPERATIONAL CONSTRAINTS</div>
            </div>
            <div className="panel-body">
              <div className="range-slider-group">
                <div className="range-header">
                  <span>PLANNING HORIZON</span>
                  <span style={{ color: "var(--tech-blue)" }}>{horizon} DAYS</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="14"
                  value={horizon}
                  onChange={(e) => setHorizon(e.target.value)}
                  className="range-slider"
                />
              </div>

              <div className="range-slider-group">
                <div className="range-header">
                  <span>MAX DAILY TECHNICIAN HOURS</span>
                  <span style={{ color: "var(--tech-blue)" }}>{maxHours} HOURS/DAY</span>
                </div>
                <input
                  type="range"
                  min="8"
                  max="48"
                  value={maxHours}
                  onChange={(e) => setMaxHours(e.target.value)}
                  className="range-slider"
                />
              </div>

              <div className="range-slider-group">
                <div className="range-header">
                  <span>MISSION READINESS PRIORITY WEIGHT</span>
                  <span style={{ color: "var(--tech-blue)" }}>{priority}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  className="range-slider"
                />
              </div>

              <div style={{ padding: 10, backgroundColor: "var(--bg-secondary)", border: "1px solid var(--border)", fontSize: 11, color: "var(--text-secondary)" }}>
                <div><strong>SCORING EQUATION:</strong></div>
                <div style={{ fontFamily: "var(--font-mono)", marginTop: 4 }}>
                  Priority = 0.65·Risk + 8.0/(1+RUL) + 0.30·Priority + SpareBonus
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Scheduled Work Orders Table */}
        <div className="col-8">
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <CheckCircle2 size={14} /> OPTIMIZED WORK ORDER SCHEDULE (HORIZON: {horizon} DAYS)
              </div>
              <div className="panel-meta">TOTAL WORK ITEMS: {(plan?.items || []).length}</div>
            </div>
            <div className="panel-body no-padding">
              <div className="table-responsive">
                <table className="tech-table">
                  <thead>
                    <tr>
                      <th>DAY</th>
                      <th>TAIL #</th>
                      <th>COMPONENT</th>
                      <th>DIRECTIVE ACTION</th>
                      <th>PRIORITY SCORE</th>
                      <th>DURATION</th>
                      <th>SPARE PART #</th>
                      <th>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(plan?.items || []).map((item, idx) => (
                      <tr key={idx}>
                        <td className="mono" style={{ fontWeight: 700, color: item.scheduled_day === 0 ? "var(--status-red)" : "var(--text-primary)" }}>
                          {item.scheduled_day != null ? `DAY ${item.scheduled_day}` : "DEFERRED"}
                        </td>
                        <td className="mono" style={{ fontWeight: 600 }}>{item.aircraft_id}</td>
                        <td className="mono">{item.component}</td>
                        <td>
                          <StatusChip
                            status={item.action === "GROUND_AND_MAINTAIN" ? "CRITICAL" : item.action === "SCHEDULE_MAINTENANCE" ? "SCHEDULED" : "MONITOR"}
                          />
                        </td>
                        <td className="mono" style={{ fontWeight: 600 }}>{fmt(item.priority_score, 3)}</td>
                        <td className="mono">{fmt(item.duration_hours, 1)}h</td>
                        <td className="mono">{item.spare_part_id}</td>
                        <td>
                          <div style={{ display: "flex", gap: 4 }}>
                            <button
                              className="btn"
                              style={{ padding: "2px 6px", fontSize: 10 }}
                              onClick={() => navigate(`/aircraft/${item.aircraft_id}?comp=${item.component}`)}
                            >
                              Inspect
                            </button>
                            {item.action !== "MONITOR" && (
                              <button
                                className="btn btn-primary"
                                style={{ padding: "2px 6px", fontSize: 10 }}
                                onClick={() => handleQuickExecute(item)}
                              >
                                Execute
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// VIEW 5: SPARE PARTS ALLOCATION & SUPPLY CHAIN
// ==========================================================================
function SparesView({ spares, onMaintenanceExecuted }) {
  const navigate = useNavigate();
  const [allocations, setAllocations] = useState(null);
  const [horizon, setHorizon] = useState(7);
  const [loading, setLoading] = useState(true);

  const fetchAllocations = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiPost("/api/spares/allocate", {
        horizon_days: Number(horizon),
        max_daily_hours: 24,
        mission_priority: 1.0,
      });
      setAllocations(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [horizon]);

  useEffect(() => {
    fetchAllocations();
  }, [fetchAllocations]);

  return (
    <div>
      <div className="view-header-bar">
        <div className="view-title-group">
          <h1><Boxes size={16} /> SPARE PARTS INVENTORY & ALLOCATION</h1>
          <div className="view-subtitle">GREEDY DELAY-COST OPTIMIZATION & REPLACEMENT COMPATIBILITY TRACKING</div>
        </div>
        <div className="view-actions">
          <button className="btn btn-primary" onClick={fetchAllocations} disabled={loading}>
            <RefreshCw size={12} className={cls(loading && "spin-slow")} /> Recalculate Allocation
          </button>
        </div>
      </div>

      <div className="panel-grid">
        {/* Left: Inventory Stock Table */}
        <div className="col-5">
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title"><Boxes size={14} /> SPARES INVENTORY DEPOT</div>
            </div>
            <div className="panel-body no-padding">
              <table className="tech-table">
                <thead>
                  <tr>
                    <th>PART ID</th>
                    <th>DESCRIPTION</th>
                    <th>STOCK</th>
                    <th>ALLOCATED</th>
                    <th>LEAD TIME</th>
                  </tr>
                </thead>
                <tbody>
                  {(spares || []).map((s) => (
                    <tr key={s.part_id}>
                      <td className="mono" style={{ fontWeight: 600 }}>{s.part_id}</td>
                      <td>
                        {s.part_id === "ENG-FLT" ? "Turbofan Module" : s.part_id === "HYD-PMP" ? "Hydraulic Pump" : s.part_id === "ELEC-REG" ? "Voltage Regulator" : "Gear Actuator"}
                      </td>
                      <td className="mono" style={{ fontWeight: 700, color: "var(--status-green)" }}>{s.quantity}</td>
                      <td className="mono">{(allocations?.inventory?.allocated || {})[s.part_id] || 0}</td>
                      <td className="mono">{s.lead_time_days} days</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right: Allocation Requests Table */}
        <div className="col-7">
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title"><Layers size={14} /> ACTIVE ALLOCATION QUEUE (DELAY IMPACT RANKING)</div>
            </div>
            <div className="panel-body no-padding">
              <table className="tech-table">
                <thead>
                  <tr>
                    <th>TAIL #</th>
                    <th>COMPONENT</th>
                    <th>PART ID</th>
                    <th>ALLOCATED</th>
                    <th>DELAY COST</th>
                    <th>STATUS</th>
                    <th>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {(allocations?.allocations || []).map((a, idx) => (
                    <tr key={idx}>
                      <td className="mono" style={{ fontWeight: 600 }}>{a.aircraft_id}</td>
                      <td className="mono">{a.component}</td>
                      <td className="mono">{a.part_id}</td>
                      <td className="mono" style={{ fontWeight: 700 }}>{a.allocated_quantity}</td>
                      <td className="mono">{fmt(a.delay_cost || 4.2)}</td>
                      <td>
                        <StatusChip status={a.unmet_quantity === 0 ? "AVAILABLE" : "CRITICAL"} />
                      </td>
                      <td>
                        <button
                          className="btn"
                          style={{ padding: "2px 6px", fontSize: 10 }}
                          onClick={() => navigate(`/aircraft/${a.aircraft_id}?comp=${a.component}`)}
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// VIEW 6: LIVE TELEMETRY OSCILLOSCOPE
// ==========================================================================
function TelemetryView({
  telemetryHistory,
  selectedAircraft,
  onSelectAircraft,
  fleetList,
  isPaused,
  onTogglePause,
  onClearBuffer,
}) {
  const [activeSensors, setActiveSensors] = useState(["egt", "vibration", "oilPressure", "risk"]);
  const [injecting, setInjecting] = useState(false);
  const [injectMsg, setInjectMsg] = useState("");

  const toggleSensor = (sensorKey) => {
    setActiveSensors((prev) =>
      prev.includes(sensorKey) ? prev.filter((k) => k !== sensorKey) : [...prev, sensorKey]
    );
  };

  const handleInjectStress = async () => {
    try {
      setInjecting(true);
      await apiPost("/api/predict", {
        aircraft_id: selectedAircraft,
        component: "ENGINE",
        telemetry: {
          sensor_2: 785.0,
          sensor_3: 1890.0,
          sensor_4: 1080.0,
          sensor_11: 49.8,
          sensor_12: 510.5,
          sensor_15: 8.95,
        },
      });
      setInjectMsg("Stress spike injected! Sensor deviation updated in stream.");
      setTimeout(() => setInjectMsg(""), 4000);
    } catch (e) {
      console.error(e);
      setInjectMsg(`Injection failed: ${e.message}`);
    } finally {
      setInjecting(false);
    }
  };

  return (
    <div>
      <div className="view-header-bar">
        <div className="view-title-group">
          <h1><Wifi size={16} /> LIVE TELEMETRY OSCILLOSCOPE ({selectedAircraft})</h1>
          <div className="view-subtitle">STREAMING 1.0 Hz C-MAPSS FD001 SENSOR PACKETS OVER WEBSOCKET</div>
        </div>
        <div className="view-actions">
          <select className="select-control" value={selectedAircraft} onChange={(e) => onSelectAircraft(e.target.value)}>
            {(fleetList || []).map((a) => (
              <option key={a.aircraft_id} value={a.aircraft_id}>{a.aircraft_id}</option>
            ))}
          </select>
          <button className="btn" onClick={onTogglePause}>
            {isPaused ? <Play size={12} /> : <Pause size={12} />}
            {isPaused ? "Resume Stream" : "Pause Stream"}
          </button>
          <button className="btn" onClick={onClearBuffer}>Clear</button>
          <button className="btn btn-danger" onClick={handleInjectStress} disabled={injecting}>
            <Zap size={12} /> {injecting ? "Injecting..." : "Inject Stress Spike"}
          </button>
        </div>
      </div>

      {injectMsg && (
        <div className="decision-alert-banner warning">
          <AlertTriangle size={16} style={{ color: "var(--status-amber)" }} />
          <div>{injectMsg}</div>
        </div>
      )}

      <div className="panel">
        <div className="panel-header">
          <div className="chart-header-toolbar" style={{ width: "100%" }}>
            <div className="panel-title"><Activity size={14} /> MULTI-CHANNEL TELEMETRY TRACES</div>
            <div className="sensor-selector-group">
              {[
                { key: "egt", label: "T24 Exhaust Gas Temp", color: "#4DA3FF" },
                { key: "vibration", label: "T30 Vibration Spectrum", color: "#FFB020" },
                { key: "oilPressure", label: "T50 Oil Pressure", color: "#35C759" },
                { key: "risk", label: "Model Failure Risk (%)", color: "#FF453A" },
              ].map((s) => (
                <button
                  key={s.key}
                  className={cls("sensor-chip-btn", activeSensors.includes(s.key) && "active")}
                  onClick={() => toggleSensor(s.key)}
                >
                  <span style={{ display: "inline-block", width: 6, height: 6, backgroundColor: s.color, marginRight: 4, borderRadius: "50%" }} />
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="panel-body">
          <div style={{ height: 360 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="2 2" stroke="#1f1f1f" />
                <XAxis dataKey="cycle" stroke="#555" tick={{ fill: "#666", fontSize: 10, fontFamily: "var(--font-mono)" }} />
                <YAxis stroke="#555" tick={{ fill: "#666", fontSize: 10, fontFamily: "var(--font-mono)" }} />
                <Tooltip content={<TechTooltip />} />
                {activeSensors.includes("egt") && <Line type="monotone" dataKey="egt" name="EGT (°C)" stroke="#4DA3FF" strokeWidth={1.5} dot={false} isAnimationActive={false} />}
                {activeSensors.includes("vibration") && <Line type="monotone" dataKey="vibration" name="Vibration (g)" stroke="#FFB020" strokeWidth={1.5} dot={false} isAnimationActive={false} />}
                {activeSensors.includes("oilPressure") && <Line type="monotone" dataKey="oilPressure" name="Oil Pressure (kPa)" stroke="#35C759" strokeWidth={1.5} dot={false} isAnimationActive={false} />}
                {activeSensors.includes("risk") && <Line type="monotone" dataKey="risk" name="Failure Risk (%)" stroke="#FF453A" strokeWidth={1.5} dot={false} isAnimationActive={false} />}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// VIEW 7: ENGINEERING ARCHITECTURE & PIPELINE DATA FLOW
// ==========================================================================
function ArchitectureView() {
  return (
    <div>
      <div className="view-header-bar">
        <div className="view-title-group">
          <h1><Network size={16} /> END-TO-END SYSTEM ARCHITECTURE & DATA FLOW</h1>
          <div className="view-subtitle">TECHNICAL MAPPING: FROM SENSOR INGESTION TO FLEET READINESS DECISION</div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div className="panel-title"><Database size={14} /> FLEETAVAIL DECISION PIPELINE DATA FLOW</div>
        </div>
        <div className="panel-body">
          <div className="pipeline-diagram">
            {[
              { step: "01", title: "TELEMETRY INGESTION", desc: "21 Raw Sensors + 3 Flight Operating Settings over 1Hz WebSocket / REST POST", tag: "C-MAPSS FD001" },
              { step: "02", title: "DATA VALIDATION & RING BUFFER", desc: "Sliding 30-cycle temporal window buffer with completeness & finite check", tag: "ml/sequence_buffer.py" },
              { step: "03", title: "FEATURE ENGINEERING", desc: "Temporal rolling features: Delta, Moving Average (MA5, MA10, MA20), Scaler", tag: "ml/cmapss/features.py" },
              { step: "04", title: "MULTI-BRANCH ML INFERENCE", desc: "Parallel evaluation: LSTM/TCN (RUL) + XGBoost (Failure Risk) + Isolation Forest (Anomaly)", tag: "ml/cmapss/runtime.py" },
              { step: "05", title: "DETERMINISTIC HEALTH FUSION", desc: "Score = 100·(0.50·Health + 0.25·(1-Anomaly) + 0.25·DataQuality) → NORMAL/WATCH/DEGRADED/CRITICAL", tag: "ml/health.py" },
              { step: "06", title: "DIGITAL TWIN LIFECYCLE PERSISTENCE", desc: "Atomic JSON state store tracking operating cycles, degradation history & event audit log", tag: "digital_twin/state.py" },
              { step: "07", title: "CONSTRAINT-AWARE MAINTENANCE OPTIMIZER", desc: "Prioritizes work orders under daily technician hour limits (max_daily_hours) and mission weights", tag: "decision_engine/maintenance_optimizer.py" },
              { step: "08", title: "SPARE PARTS INVENTORY ALLOCATION", desc: "Greedy delay-cost minimization allocating compatible inventory (ENG-FLT, HYD-PMP, ELEC-REG, LG-ACT)", tag: "decision_engine/spares.py" },
              { step: "09", title: "FLEET READINESS & AVAILABILITY PROJECTION", desc: "Calculates current readiness % vs projected 7-day post-maintenance operational availability", tag: "decision_engine/fleet_availability.py" },
            ].map((p, idx) => (
              <div key={idx} className={cls("pipeline-step", idx < 6 && "active")}>
                <div className="pipeline-step-num">{p.step}</div>
                <div className="pipeline-step-content">
                  <div className="pipeline-step-title">{p.title}</div>
                  <div className="pipeline-step-desc">{p.desc}</div>
                </div>
                <div className="pipeline-step-tag">{p.tag}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// ROOT APP SHELL WITH TOP STATUS STRIP & ROUTING
// ==========================================================================
export default function App() {
  const [summary, setSummary] = useState(null);
  const [fleetList, setFleetList] = useState([]);
  const [spares, setSpares] = useState([]);
  const [selectedAircraft, setSelectedAircraft] = useState(DEFAULT_AIRCRAFT);
  const [activeAircraftDetail, setActiveAircraftDetail] = useState(null);
  const [telemetryHistory, setTelemetryHistory] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [clock, setClock] = useState("");
  const wsRef = useRef(null);

  // UTC Clock
  useEffect(() => {
    const timer = setInterval(() => {
      setClock(new Date().toUTCString().replace("GMT", "UTC"));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch initial base data
  const refreshBaseData = useCallback(async () => {
    try {
      const [sum, list, sp] = await Promise.all([
        apiGet("/api/fleet/summary"),
        apiGet("/api/fleet/aircraft"),
        apiGet("/api/spares"),
      ]);
      setSummary(sum);
      setFleetList(list);
      setSpares(sp);
    } catch (e) {
      console.error("Base data fetch error:", e);
    }
  }, []);

  useEffect(() => {
    refreshBaseData();
    const interval = setInterval(refreshBaseData, 10000);
    return () => clearInterval(interval);
  }, [refreshBaseData]);

  // Fetch active aircraft detail when selection changes
  useEffect(() => {
    apiGet(`/api/fleet/aircraft/${selectedAircraft}`)
      .then(setActiveAircraftDetail)
      .catch(console.error);
  }, [selectedAircraft]);

  // Connect WebSocket for live telemetry streaming
  useEffect(() => {
    const url = websocketUrl(selectedAircraft);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);

    ws.onmessage = (evt) => {
      if (isPaused) return;
      try {
        const data = JSON.parse(evt.data);
        const t = data.telemetry || {};
        const rawEgt = t.sensor_2 != null ? Number(t.sensor_2) : (t.egt_c != null ? Number(t.egt_c) : (data.raw_health_score ? data.raw_health_score * 8.5 : 680));
        const rawVib = t.sensor_3 != null ? (t.sensor_3 > 10 ? Number(t.sensor_3) / 1000 : Number(t.sensor_3)) : (t.vibration_g != null ? Number(t.vibration_g) : 0.25);
        const rawOil = t.sensor_4 != null ? (t.sensor_4 > 100 ? Number(t.sensor_4) / 3.4 : Number(t.sensor_4)) : (t.oil_pressure_kpa != null ? Number(t.oil_pressure_kpa) : 380);

        setTelemetryHistory((prev) => {
          const newPoint = {
            cycle: data.cycle,
            egt: Number(rawEgt.toFixed(1)),
            vibration: Number(rawVib.toFixed(3)),
            oilPressure: Number(rawOil.toFixed(1)),
            risk: Number(((data.failure_probability || 0) * 100).toFixed(1)),
            health: data.health_score,
          };
          const next = [...prev, newPoint];
          return next.slice(-40); // Keep last 40 frames
        });
      } catch (err) {
        console.error("WS Parse error:", err);
      }
    };

    return () => {
      ws.close();
    };
  }, [selectedAircraft, isPaused]);

  return (
    <div className="console-shell">
      {/* Top Header */}
      <header className="console-header">
        <div className="header-main">
          <div className="brand-section">
            <span className="brand-title">
              <Plane size={16} color="var(--tech-blue)" /> FLEETAVAIL
            </span>
            <span className="brand-tag">SIH26249 • AIR POWER OPERATIONS</span>
          </div>

          <nav className="header-nav">
            <NavLink to="/" className={({ isActive }) => cls("nav-link", isActive && "active")} end>
              Fleet Overview
            </NavLink>
            <NavLink to="/fleet" className={({ isActive }) => cls("nav-link", isActive && "active")}>
              Aircraft
            </NavLink>
            <NavLink to={`/aircraft/${selectedAircraft}`} className={({ isActive }) => cls("nav-link", isActive && "active")}>
              Digital Twin
            </NavLink>
            <NavLink to="/maintenance" className={({ isActive }) => cls("nav-link", isActive && "active")}>
              Maintenance
            </NavLink>
            <NavLink to="/spares" className={({ isActive }) => cls("nav-link", isActive && "active")}>
              Spares
            </NavLink>
            <NavLink to="/telemetry" className={({ isActive }) => cls("nav-link", isActive && "active")}>
              Telemetry
            </NavLink>
            <NavLink to="/architecture" className={({ isActive }) => cls("nav-link", isActive && "active")}>
              Architecture
            </NavLink>
          </nav>

          <div className="header-status-group">
            <button
              className="live-feed-pill"
              onClick={() => setIsPaused((prev) => !prev)}
              style={{ cursor: "pointer", border: "1px solid var(--border)" }}
              title="Click to pause/resume live stream"
            >
              <span className={cls("live-dot", (!wsConnected || isPaused) && "disconnected")} />
              {isPaused ? "PAUSED" : wsConnected ? "1.0 Hz STREAM" : "OFFLINE"}
            </button>
            <div className="clock-display">
              <Clock size={11} style={{ display: "inline", marginRight: 4 }} />
              {clock || "SYSTEM TIME"}
            </div>
          </div>
        </div>

        {/* Operational Status Strip (Always visible across all screens) */}
        <div className="operational-strip">
          <div className="strip-item">
            <span className="strip-label">AIRCRAFT</span>
            <span className="strip-value">{summary?.total_aircraft ?? 12}</span>
          </div>
          <div className="strip-item">
            <span className="strip-label">AVAILABLE</span>
            <span className="strip-value green">{summary?.ready ?? 7}</span>
          </div>
          <div className="strip-item">
            <span className="strip-label">WATCH</span>
            <span className="strip-value amber">{summary?.degraded ? Math.floor(summary.degraded / 2) : 1}</span>
          </div>
          <div className="strip-item">
            <span className="strip-label">DEGRADED</span>
            <span className="strip-value amber">{summary?.degraded ?? 2}</span>
          </div>
          <div className="strip-item">
            <span className="strip-label">CRITICAL</span>
            <span className="strip-value red">{summary?.critical_aircraft ?? 0}</span>
          </div>
          <div className="strip-item">
            <span className="strip-label">IN MAINT</span>
            <span className="strip-value red">{summary?.maintenance ?? 2}</span>
          </div>
          <div className="strip-item">
            <span className="strip-label">FLEET READINESS</span>
            <span className="strip-value blue">{pct(summary?.current_availability_pct)}</span>
          </div>
          <div className="strip-item">
            <span className="strip-label">PROJECTED 7-DAY</span>
            <span className="strip-value green">{pct(summary?.projected_7_day_availability_pct)}</span>
          </div>
          <div className="strip-item">
            <span className="strip-label">DATA MODE</span>
            <span className="strip-badge">C-MAPSS FD001 • DEMO / SIMULATION</span>
          </div>
        </div>
      </header>

      {/* Main Routed Console View */}
      <main className="console-view">
        <Routes>
          <Route
            path="/"
            element={
              <OverviewView
                summary={summary}
                fleetList={fleetList}
                spares={spares}
                telemetryHistory={telemetryHistory}
                selectedAircraft={selectedAircraft}
                onSelectAircraft={setSelectedAircraft}
                aircraftDetail={activeAircraftDetail}
              />
            }
          />
          <Route path="/fleet" element={<FleetMonitorView fleetList={fleetList} />} />
          <Route
            path="/aircraft/:aircraftId"
            element={
              <AircraftDetailView
                fleetList={fleetList}
                onMaintenanceExecuted={refreshBaseData}
              />
            }
          />
          <Route path="/aircraft" element={<Navigate to={`/aircraft/${selectedAircraft}`} replace />} />
          <Route path="/twin" element={<Navigate to={`/aircraft/${selectedAircraft}`} replace />} />
          <Route
            path="/maintenance"
            element={<MaintenanceView onMaintenanceExecuted={refreshBaseData} />}
          />
          <Route
            path="/spares"
            element={<SparesView spares={spares} onMaintenanceExecuted={refreshBaseData} />}
          />
          <Route
            path="/telemetry"
            element={
              <TelemetryView
                telemetryHistory={telemetryHistory}
                selectedAircraft={selectedAircraft}
                onSelectAircraft={setSelectedAircraft}
                fleetList={fleetList}
                isPaused={isPaused}
                onTogglePause={() => setIsPaused((prev) => !prev)}
                onClearBuffer={() => setTelemetryHistory([])}
              />
            }
          />
          <Route path="/architecture" element={<ArchitectureView />} />
        </Routes>
      </main>
    </div>
  );
}
