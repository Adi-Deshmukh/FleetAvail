import React, {useCallback,useEffect,useMemo,useState} from "react";
import {Activity,AlertTriangle,BarChart3,Boxes,BrainCircuit,ChevronRight,Cpu,Gauge,GitBranch,Layers3,Menu,Network,Plane,RefreshCw,ShieldCheck,Wrench,X,Zap} from "lucide-react";
import {NavLink,Route,Routes,useParams} from "react-router-dom";
import {Bar,BarChart,CartesianGrid,Cell,Line,LineChart,Pie,PieChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from "recharts";
import {apiGet,apiPost,websocketUrl} from "./api";

const nav=[
 {to:"/",label:"Overview",icon:Gauge},{to:"/fleet",label:"Fleet",icon:Plane},
 {to:"/models",label:"Models & pipeline",icon:BrainCircuit},{to:"/operations",label:"Operations",icon:Wrench},
 {to:"/aircraft/AF-001",label:"Aircraft detail",icon:Activity}
];

function useData(loader,deps=[]){
 const [s,setS]=useState({data:null,loading:true,error:null});
 const reload=useCallback(async()=>{setS(x=>({...x,loading:true,error:null}));try{setS({data:await loader(),loading:false,error:null})}catch(e){setS({data:null,loading:false,error:e.message})}},deps);
 useEffect(()=>{reload()},[reload]); return {...s,reload};
}
const cls=(...x)=>x.filter(Boolean).join(" ");
const fmt=(v,d=1)=>v==null||Number.isNaN(Number(v))?"—":Number(v).toFixed(d);
const pct=v=>v==null?"—":((Number(v)<=1?Number(v)*100:Number(v)).toFixed(1)+"%");
const sc=v=>String(v||"UNKNOWN").toLowerCase().replaceAll("_","-");

function Badge({value}){return <span className={cls("badge",sc(value))}>{String(value||"UNKNOWN").replaceAll("_"," ")}</span>}
function Loading({text="Loading live backend data…"}){return <div className="loading"><RefreshCw size={16} className="spin"/>{text}</div>}
function ErrorState({error,retry}){return <div className="error"><AlertTriangle size={17}/><div><strong>Backend data unavailable</strong><span>{error}</span></div><button onClick={retry}>Retry</button></div>}
function Header({eyebrow,title,description,action}){return <header className="page-head"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{description&&<p>{description}</p>}</div>{action}</header>}
function Card({title,subtitle,children,action,className=""}){return <section className={cls("card",className)}>{(title||action)&&<div className="card-head"><div>{title&&<h2>{title}</h2>}{subtitle&&<p>{subtitle}</p>}</div>{action}</div>}{children}</section>}
function KPI({label,value,detail,icon:Icon,tone=""}){return <div className={cls("kpi",tone)}><div className="kpi-head"><span>{label}</span><i><Icon size={16}/></i></div><strong>{value}</strong>{detail&&<small>{detail}</small>}</div>}
function Metric({label,value}){return <div className="metric"><span>{label}</span><strong>{value}</strong></div>}

function App(){
 const [mobile,setMobile]=useState(false),[health,setHealth]=useState(null),[telemetry,setTelemetry]=useState(null);
 useEffect(()=>{apiGet("/health").then(setHealth).catch(()=>{});let socket,retry;const connect=()=>{socket=new WebSocket(websocketUrl());socket.onmessage=e=>setTelemetry(JSON.parse(e.data));socket.onclose=()=>retry=setTimeout(connect,2500)};connect();return()=>{clearTimeout(retry);socket?.close()}},[]);
 return <div className="shell">
  <aside className={cls("sidebar",mobile&&"open")}>
   <div className="brand"><div className="brand-mark"><Network size={19}/></div><div><b>FleetAvail</b><span>Control plane</span></div><button className="mobile-close" onClick={()=>setMobile(false)}><X size={18}/></button></div>
   <div className="backend"><span className={cls("dot",health?.status==="healthy"&&"live")}/><span>Backend {health?.status==="healthy"?"online":"checking"}</span><em>{health?.mode||"—"}</em></div>
   <nav>{nav.map(n=>{const I=n.icon;return <NavLink key={n.to} to={n.to} end={n.to==="/"} onClick={()=>setMobile(false)}><I size={17}/>{n.label}</NavLink>})}</nav>
   <div className="side-foot"><label>DATASET</label><span>NASA C-MAPSS · FD001</span><label>FLOW</label><div>Telemetry → ML → Decisions</div></div>
  </aside>
  {mobile&&<div className="overlay" onClick={()=>setMobile(false)}/>}
  <div className="mobilebar"><button onClick={()=>setMobile(true)}><Menu size={20}/></button><b>FleetAvail</b></div>
  <main><Routes>
   <Route path="/" element={<Overview telemetry={telemetry}/>}/><Route path="/fleet" element={<Fleet/>}/>
   <Route path="/models" element={<Models/>}/><Route path="/operations" element={<Operations/>}/>
   <Route path="/aircraft/:aircraftId" element={<Aircraft/>}/>
  </Routes></main>
 </div>
}

function Overview({telemetry}){
 const s=useData(()=>apiGet("/api/fleet/summary")),f=useData(()=>apiGet("/api/fleet/aircraft")),m=useData(()=>apiGet("/api/models")),o=useData(()=>apiGet("/api/observability"));
 if(s.loading)return <><Header eyebrow="COMMAND CENTER" title="Fleet overview" description="Live aircraft predictive-maintenance control plane."/><Loading/></>;
 if(s.error)return <ErrorState error={s.error} retry={s.reload}/>;
 const dist=useMemo(()=>{const x={};(f.data||[]).forEach(a=>{const k=a.engine?.operational_state||"UNKNOWN";x[k]=(x[k]||0)+1});return Object.entries(x).map(([name,value])=>({name,value}))},[f.data]);
 return <>
  <Header eyebrow="COMMAND CENTER · LIVE" title="Fleet overview" description="Telemetry → model inference → health fusion → digital twin → maintenance → spares → availability." action={<Live telemetry={telemetry}/>}/>
  <div className="kpis">
   <KPI label="Current availability" value={fmt(s.data.current_availability_pct)+"%"} detail="Fleet readiness now" icon={Gauge} tone="good"/>
   <KPI label="7-day projected" value={fmt(s.data.projected_7_day_availability_pct)+"%"} detail="After planned maintenance" icon={BarChart3}/>
   <KPI label="Ready aircraft" value={s.data.ready+" / "+s.data.total_aircraft} detail="Current fleet status" icon={Plane}/>
   <KPI label="Critical aircraft" value={s.data.critical_aircraft} detail="Engine health state" icon={AlertTriangle} tone={s.data.critical_aircraft?"bad":""}/>
   <KPI label="Degraded / maintenance" value={s.data.degraded+" / "+s.data.maintenance} detail="Fleet status" icon={Wrench}/>
  </div>
  <div className="two">
   <Card title="Fleet health state" subtitle="Live engine health-fusion classification."><ChartBox><BarChart data={dist}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="name"/><YAxis allowDecimals={false}/><Tooltip/><Bar dataKey="value" name="Aircraft" radius={[5,5,0,0]}>{dist.map((_,i)=><Cell key={i}/>)}</Bar></BarChart></ChartBox></Card>
   <Card title="Live telemetry" subtitle="WebSocket event from FastAPI."><Telemetry data={telemetry}/></Card>
  </div>
  <Card title="End-to-end system dataflow" subtitle="Every stage is backed by a FleetAvail subsystem."><Flow models={m.data}/></Card>
  <div className="two">
   <Card title="Fleet snapshot" subtitle="GET /api/fleet/aircraft"><FleetTable rows={f.data||[]} compact/></Card>
   <Card title="Runtime observability" subtitle="GET /api/observability"><Obs data={o.data}/></Card>
  </div>
 </>
}

function Live({telemetry}){return <div className="live"><span className="dot live"/><div><b>Live</b><small>{telemetry?telemetry.aircraft_id+" · "+telemetry.component:"Connecting…"}</small></div></div>}
function Telemetry({data}){if(!data)return <Loading text="Waiting for telemetry…"/>;return <div className="telemetry">{[["Aircraft",data.aircraft_id],["Component",data.component],["Health",fmt(data.health_score)],["RUL",fmt(data.rul_cycles,0)+" cycles"],["Risk",pct(data.failure_probability)],["State",<Badge value={data.health_level}/>]].map(([k,v])=><div key={k}><span>{k}</span><b>{v}</b></div>)}</div>}
function Flow({models}){
 const stages=[["01","Telemetry","21 sensors + 3 operating settings"],["02","Validation","Normalization · quality · 30-cycle buffer"],["03","ML inference","RUL · failure risk · anomaly"],["04","Health fusion","Health score · state"],["05","Digital twin","State + event history"],["06","Maintenance","Priority · schedule"],["07","Spares","Allocation · inventory"],["08","Availability","Current + projected readiness"]];
 return <div className="flow">{stages.map((x,i)=><React.Fragment key={x[0]}><div className="flow-node"><small>{x[0]}</small><b>{x[1]}</b><span>{x[2]}</span></div>{i<stages.length-1&&<ChevronRight className="flow-arrow" size={16}/>}</React.Fragment>)}<div className="runtime"><Cpu size={14}/> {models?.mode||"runtime"} · RUL <b>{models?.rul_selection?.selected||"unavailable"}</b></div></div>
}
function Obs({data}){if(!data)return <Loading/>;const m=data.metrics||{};return <div className="metrics"><Metric label="Predictions" value={m.predictions_total??0}/><Metric label="Mean latency" value={fmt(m.latency_ms?.mean,2)+" ms"}/><Metric label="P95 latency" value={fmt(m.latency_ms?.p95,2)+" ms"}/><Metric label="Audit retained" value={m.audit_records_retained??0}/><Metric label="Tracked pairs" value={m.tracked_aircraft_components??0}/><Metric label="Version" value={m.phase_c_version||"—"}/></div>}
function ChartBox({children}){return <div className="chart"><ResponsiveContainer width="100%" height={285}>{children}</ResponsiveContainer></div>}

function Fleet(){
 const f=useData(()=>apiGet("/api/fleet/aircraft")),a=useData(()=>apiGet("/api/fleet/availability")),[filter,setFilter]=useState("ALL");
 if(f.loading)return <><Header eyebrow="FLEET" title="Aircraft fleet"/><Loading/></>;if(f.error)return <ErrorState error={f.error} retry={f.reload}/>;
 const rows=f.data||[],filtered=rows.filter(x=>filter==="ALL"||x.status===filter||x.engine?.operational_state===filter);
 const risk=rows.map(x=>({aircraft:x.aircraft_id,risk:Number(x.engine?.failure_probability||0)*100})).sort((x,y)=>y.risk-x.risk);
 return <><Header eyebrow="FLEET MONITORING" title="Aircraft fleet" description="Current aircraft state from the live fleet service."/>
 <div className="kpis four"><KPI label="Aircraft" value={rows.length} icon={Plane}/><KPI label="Current availability" value={fmt(a.data?.current_availability_pct)+"%"} icon={Gauge}/><KPI label="Projected availability" value={fmt(a.data?.projected_availability_pct)+"%"} icon={BarChart3}/><KPI label="Plan items" value={a.data?.maintenance_plan_items??"—"} icon={Wrench}/></div>
 <Card title="Failure-risk ranking" subtitle="Model-derived engine failure probability."><ChartBox><BarChart data={risk} layout="vertical" margin={{left:5,right:25}}><CartesianGrid strokeDasharray="3 3" horizontal={false}/><XAxis type="number" domain={[0,100]}/><YAxis type="category" dataKey="aircraft" width={60}/><Tooltip/><Bar dataKey="risk" name="Risk %" radius={[0,5,5,0]}/></BarChart></ChartBox></Card>
 <Card title="Aircraft records" action={<select value={filter} onChange={e=>setFilter(e.target.value)}><option>ALL</option><option>READY</option><option>DEGRADED</option><option>MAINTENANCE</option><option>CRITICAL</option><option>WATCH</option></select>}><FleetTable rows={filtered}/></Card></>
}
function FleetTable({rows,compact=false}){if(!rows.length)return <div className="empty">No records returned by the backend.</div>;return <div className="table-wrap"><table><thead><tr><th>Aircraft</th><th>Status</th><th>Health</th><th>RUL</th><th>Risk</th><th>Anomaly</th><th>State</th></tr></thead><tbody>{rows.map(a=>{const e=a.engine||{};return <tr key={a.aircraft_id}><td><NavLink className="link" to={"/aircraft/"+a.aircraft_id}>{a.aircraft_id}</NavLink></td><td><Badge value={a.status}/></td><td>{fmt(e.health_score)}</td><td>{fmt(e.rul_cycles,0)} cyc</td><td>{pct(e.failure_probability)}</td><td>{pct(e.anomaly_score)}</td><td><Badge value={e.operational_state}/></td></tr>})}</tbody></table></div>}

function Models(){
 const {data:m,loading,error,reload}=useData(()=>apiGet("/api/models"));
 if(loading)return <><Header eyebrow="ML SYSTEM" title="Models & pipeline"/><Loading/></>;if(error)return <ErrorState error={error} retry={reload}/>;
 const c=m?.rul_selection?.comparison, rows=c?[{model:"HistGradientBoosting",mae:c.baseline?.mae,rmse:c.baseline?.rmse},{model:"LSTM",mae:c.models?.lstm?.mae,rmse:c.models?.lstm?.rmse},{model:"TCN",mae:c.models?.tcn?.mae,rmse:c.models?.tcn?.rmse}].filter(x=>x.mae!=null):[];
 return <><Header eyebrow="ML SYSTEM" title="Models & inference pipeline" description="Runtime state and validated FD001 model comparison returned by the backend."/>
 <div className="kpis four"><KPI label="Runtime" value={m.mode||"—"} detail="Backend mode" icon={Cpu}/><KPI label="Selected RUL" value={m.rul_selection?.selected||"—"} detail={m.rul_selection?.reason||"—"} icon={BrainCircuit} tone="good"/><KPI label="Window" value={m.required_window??"—"} detail="cycles" icon={Layers3}/><KPI label="Loaded branches" value={Object.keys(m.branches||{}).length} detail="RUL / risk / anomaly" icon={GitBranch}/></div>
 <div className="two"><Card title="Active model branches" subtitle="Actual loaded artifacts.">{Object.keys(m.branches||{}).length?<div className="branches">{Object.entries(m.branches).map(([k,b])=><div className="branch" key={k}><Cpu size={16}/><div><b>{k.toUpperCase()}</b><span>{b.model}</span></div><Badge value="LOADED"/></div>)}</div>:<div className="empty">No trained artifacts are loaded in this runtime.</div>}</Card>
 <Card title="Inference contract" subtitle="Runtime boundary used by FastAPI."><div className="contract"><Metric label="Dataset" value="NASA C-MAPSS FD001"/><Metric label="Inputs" value="3 settings + 21 sensors"/><Metric label="Sequence" value={(m.required_window??30)+" cycles"}/><Metric label="Outputs" value="RUL + failure risk + anomaly"/><Metric label="Cold start" value="< sequence window"/><Metric label="Selection" value={m.rul_selection?.requested||"auto"}/></div></Card></div>
 <Card title="RUL benchmark comparison" subtitle="Only renders metrics returned by the runtime comparison artifact."><div className="two">{rows.length?<><Card title="MAE"><ChartBox><BarChart data={rows}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="model"/><YAxis/><Tooltip/><Bar dataKey="mae" name="MAE" radius={[5,5,0,0]}/></BarChart></ChartBox></Card><Card title="RMSE"><ChartBox><BarChart data={rows}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="model"/><YAxis/><Tooltip/><Bar dataKey="rmse" name="RMSE" radius={[5,5,0,0]}/></BarChart></ChartBox></Card></>:<div className="empty large"><BrainCircuit size={22}/><b>Benchmark artifact not loaded</b><span>The backend returned no comparison metrics. Load the FD001 comparison artifact to populate these charts.</span></div>}</div></Card>
 <Card title="Model-selection decision"><div className="decision"><ShieldCheck size={19}/><div><b>{m.rul_selection?.selected||"Unavailable"}</b><span>{m.rul_selection?.reason||"No selection reason returned."}</span></div></div></Card></>
}

function Operations(){
 const o=useData(()=>apiGet("/api/observability")),p=useData(()=>apiPost("/api/maintenance/plan",{mission_priority:1,horizon_days:7,max_daily_hours:24})),sp=useData(()=>apiGet("/api/spares")),al=useData(()=>apiPost("/api/spares/allocate",{mission_priority:1,horizon_days:7,max_daily_hours:24}));
 if(o.loading)return <><Header eyebrow="OPERATIONS" title="Decision operations"/><Loading/></>;if(o.error)return <ErrorState error={o.error} retry={o.reload}/>;
 const m=o.data.metrics||{},status=Object.entries(m.status_counts||{}).map(([name,value])=>({name,value}));
 return <><Header eyebrow="OPERATIONS" title="Decision operations" description="Maintenance planning, spare allocation, observability and auditability."/>
 <div className="kpis four"><KPI label="Predictions" value={m.predictions_total??0} icon={Activity}/><KPI label="P95 latency" value={fmt(m.latency_ms?.p95,2)+" ms"} icon={Zap}/><KPI label="Audit retained" value={m.audit_records_retained??0} icon={ShieldCheck}/><KPI label="Spare unmet" value={al.data?.inventory?.total_unmet??"—"} icon={Boxes} tone={al.data?.inventory?.total_unmet?"bad":""}/></div>
 <div className="two"><Card title="Prediction lifecycle" subtitle="Observed status counts."><ChartBox><PieChart><Pie data={status} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>{status.map((_,i)=><Cell key={i}/>)}</Pie><Tooltip/></PieChart></ChartBox></Card><Card title="Latency metrics"><div className="latency"><Metric label="Last" value={fmt(m.latency_ms?.last,2)+" ms"}/><Metric label="Mean" value={fmt(m.latency_ms?.mean,2)+" ms"}/><Metric label="P95" value={fmt(m.latency_ms?.p95,2)+" ms"}/></div></Card></div>
 <div className="two"><Card title="Maintenance plan" subtitle="7-day plan from the backend optimizer."><Plan rows={p.data?.items||[]}/></Card><Card title="Spare inventory" subtitle="GET /api/spares"><div className="table-wrap"><table><thead><tr><th>Part</th><th>Qty</th><th>Lead time</th></tr></thead><tbody>{(sp.data||[]).map(x=><tr key={x.part_id}><td>{x.part_id}</td><td>{x.quantity}</td><td>{x.lead_time_days} days</td></tr>)}</tbody></table></div><div className="note">Allocation requests: {al.data?.requests?.length??0} · unmet: {al.data?.inventory?.total_unmet??"—"}</div></Card></div>
 <Card title="Recent audit records"><Audit rows={o.data.latest_audits||[]}/></Card></>
}
function Plan({rows}){return <div className="table-wrap"><table><thead><tr><th>Aircraft</th><th>Component</th><th>Action</th><th>Day</th><th>Priority</th></tr></thead><tbody>{rows.slice(0,20).map((x,i)=><tr key={i}><td>{x.aircraft_id}</td><td>{x.component}</td><td>{x.action}</td><td>Day {x.scheduled_day}</td><td>{fmt(x.priority_score,2)}</td></tr>)}</tbody></table></div>}
function Audit({rows}){if(!rows.length)return <div className="empty">No prediction audit records yet. Send telemetry to /api/predict.</div>;return <div className="table-wrap"><table><thead><tr><th>Time</th><th>Aircraft</th><th>Cycle</th><th>Status</th><th>Latency</th><th>Quality</th><th>RUL</th><th>Risk</th></tr></thead><tbody>{[...rows].reverse().map((r,i)=><tr key={i}><td>{new Date(r.timestamp).toLocaleTimeString()}</td><td>{r.aircraft_id}</td><td>{r.cycle}</td><td><Badge value={r.status}/></td><td>{fmt(r.latency_ms,2)} ms</td><td>{pct(r.telemetry_quality?.score)}</td><td>{r.prediction?.rul_cycles??"—"}</td><td>{pct(r.prediction?.failure_probability)}</td></tr>)}</tbody></table></div>}

function Aircraft(){
 const {aircraftId}=useParams(),d=useData(()=>apiGet("/api/fleet/aircraft/"+aircraftId),[aircraftId]),[deg,setDeg]=useState(20),[what,setWhat]=useState(null);
 if(d.loading)return <><Header eyebrow="AIRCRAFT" title={aircraftId}/><Loading/></>;if(d.error)return <ErrorState error={d.error} retry={d.reload}/>;
 const e=d.data.components?.ENGINE||{}, comps=Object.entries(d.data.components||{}).map(([name,x])=>({name,health:x.health_score,rul:x.rul_cycles,risk:x.failure_probability}));
 async function run(){try{setWhat(await apiPost("/api/simulate/what-if",{aircraft_id:aircraftId,component:"ENGINE",degradation_pct:Number(deg)}))}catch(x){setWhat({error:x.message})}}
 return <><Header eyebrow="AIRCRAFT DETAIL" title={aircraftId} description="Digital twin and model-derived state." action={<Badge value={d.data.status}/>}/>
 <div className="kpis four"><KPI label="Engine health" value={fmt(e.health_score)} detail={e.health_level} icon={Gauge}/><KPI label="RUL" value={fmt(e.rul_cycles,0)+" cycles"} detail={e.lifecycle_status} icon={Activity}/><KPI label="Failure risk" value={pct(e.failure_probability)} detail="Model-derived" icon={AlertTriangle}/><KPI label="Anomaly" value={pct(e.anomaly_score)} detail="Model-derived" icon={Zap}/></div>
 <div className="two"><Card title="Component health"><ChartBox><BarChart data={comps}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="name"/><YAxis domain={[0,100]}/><Tooltip/><Bar dataKey="health" name="Health score" radius={[5,5,0,0]}/></BarChart></ChartBox></Card><Card title="Digital twin state"><div className="contract"><Metric label="Mission status" value={d.data.twin_state?.mission_status||"—"}/><Metric label="Location" value={d.data.twin_state?.location||"—"}/><Metric label="Maintenance due" value={String(d.data.twin_state?.maintenance_due)}/><Metric label="Engine cycle" value={d.data.twin_state?.components?.ENGINE?.last_update_cycle??"—"}/><Metric label="Events retained" value={d.data.twin_state?.events?.length??0}/><Metric label="Model" value={e.model_version||"—"}/></div></Card></div>
 <div className="two"><Card title="What-if degradation" subtitle="Live POST /api/simulate/what-if"><div className="form"><input type="number" min="-50" max="200" value={deg} onChange={x=>setDeg(x.target.value)}/><span>% degradation</span><button onClick={run}>Simulate</button></div>{what&&<div className="compare"><Metric label="Baseline health" value={fmt(what.baseline?.health_score)}/><Metric label="Scenario health" value={fmt(what.scenario?.health_score)}/><Metric label="Scenario RUL" value={fmt(what.scenario?.rul_cycles,0)+" cycles"}/><Metric label="Projected fleet availability" value={fmt(what.scenario?.projected_fleet_availability_pct)+"%"}/></div>}</Card><Card title="Twin event timeline"><div className="timeline">{[...(d.data.twin_state?.events||[])].reverse().slice(0,12).map((x,i)=><div key={i}><i/><span><b>{x.event_type}</b>Cycle {x.cycle} · {new Date(x.timestamp).toLocaleString()}</span></div>)}</div></Card></div>
 </>;
}
export default App;
