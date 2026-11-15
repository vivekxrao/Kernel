import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertTriangle, ArrowRight, Bell, Building2, CalendarDays,
  CheckCircle2, Clock3, Download, FileText, Globe2, Layers3, Map,
  MapPinned, Plus, RefreshCw, Satellite, Search, ShieldCheck, Signal,
  SlidersHorizontal, TrendingUp
} from 'lucide-react';
import DamageMap from './components/DamageMap.jsx';
import SatelliteComparison from './components/SatelliteComparison.jsx';
import {
  csvExportUrl, getBuildings, getConfig, getHealth, getSummary, submitAssessment
} from './lib/api.js';

const EMPTY = { type: 'FeatureCollection', features: [] };
const NAV = [
  ['dashboard', 'Dashboard', Globe2],
  ['assessment', 'New Assessment', Plus],
  ['comparison', 'Satellite Comparison', Map],
  ['analysis', 'Damage Analysis', TrendingUp],
  ['reports', 'Intelligence Reports', FileText],
];

function StatCard({ icon: Icon, label, value, note, tone = 'cyan' }) {
  return <article className="kd-stat-card"><div className="kd-stat-head"><span>{label}</span><Icon size={18} className={tone}/></div><strong>{value}</strong><small>{note}</small></article>;
}

function Sidebar({ active, onNavigate, engineOnline }) {
  return <aside className="kd-sidebar">
    <div className="kd-logo"><div className="kd-logo-mark"><Globe2 size={29}/></div><div><b>KERNEL</b><small>DAMAGE INTELLIGENCE</small></div></div>
    <div className="kd-sidebar-caption">WORKSPACE</div>
    <nav className="kd-navigation">{NAV.map(([id, label, Icon]) => <button key={id} className={`kd-nav-item ${active === id ? 'active' : ''}`} onClick={() => onNavigate(id)}><Icon size={19}/><span>{label}</span>{active === id && <i/>}</button>)}</nav>
    <div className="kd-sidebar-bottom">
      <div className="kd-sidebar-caption">STUDY AREAS</div>
      <button className="kd-area-link" onClick={() => onNavigate('dashboard')}><i/> Bakhmut, Ukraine <small>PRIMARY</small></button>
      <div className="kd-sidebar-engine"><div className="kd-engine-line"><i className={engineOnline ? 'online' : 'offline'}/>Engine Status<b className={engineOnline ? 'online-text' : 'offline-text'}>{engineOnline ? 'Online' : 'Offline'}</b></div><small>FastAPI / Google Earth Engine</small><small>127.0.0.1:8000</small></div>
      <div className="kd-sidebar-footer">KERNEL · HACKNAUTS 2.0</div>
    </div>
  </aside>;
}

function Topbar({ title, engineOnline, onRefresh, loading }) {
  return <header className="kd-topbar"><div className="kd-breadcrumb"><span>Geospatial Intelligence Platform</span><b>/</b>{title}</div><div className="kd-top-actions"><span className={`kd-top-online ${engineOnline ? '' : 'offline'}`}><i/>{engineOnline ? 'ENGINE ONLINE' : 'ENGINE OFFLINE'}</span><button className="kd-icon-btn" onClick={onRefresh} title="Refresh data" disabled={loading}><RefreshCw size={17}/></button><div className="kd-avatar">K</div></div></header>;
}

function StatusCard({ icon: Icon, label, value, detail, status }) {
  return <article className="kd-status-card"><div className="kd-status-icon"><Icon size={23}/></div><div><small>{label}</small><b>{value}</b>{status ? <span className="kd-status-good"><i/>{detail}</span> : <span>{detail}</span>}</div></article>;
}

function BuildingInspection({ building, threshold, onClose }) {
  if (!building) return <div className="kd-inspection-empty"><MapPinned size={30}/><b>No building selected</b><span>Select a building polygon on the map to inspect its PWTT screening values.</span></div>;
  const mean = Number(building.mean_t);
  const flagged = Number.isFinite(mean) && mean > threshold;
  return <div className="kd-inspection"><div className="kd-inspection-title"><div className="kd-building-symbol"><Building2 size={22}/></div><div><b>Building {building.building_id ?? building.id ?? '—'}</b><small>Individual screening record</small></div><button onClick={onClose} aria-label="Clear selected building"><X size={16}/></button></div>
    <div className="kd-score-highlight"><small>MEAN PWTT T-STATISTIC</small><strong>{Number.isFinite(mean) ? mean.toFixed(2) : '—'}</strong><span>Change indicator · not a probability</span></div>
    <div className="kd-inspection-metric"><span>Maximum T-score</span><b>{building.max_t == null ? '—' : Number(building.max_t).toFixed(2)}</b></div>
    <div className="kd-inspection-metric"><span>Valid raster pixels</span><b>{building.valid_pixels ?? '—'}</b></div>
    <div className="kd-inspection-metric"><span>Screening threshold</span><b>T &gt; {threshold}</b></div>
    <div className="kd-inspection-metric"><span>Screening status</span><b className={flagged ? 'amber-text' : 'green-text'}>{building.screening_status || (flagged ? 'Flagged for review' : 'Below threshold')}</b></div>
    <div className="kd-review-warning"><ShieldCheck size={17}/><span>Human verification required before treating this as physical damage.</span></div>
  </div>;
}

function Dashboard({ summary, data, config, loading, error, updated, selected, setSelected, onRefresh }) {
  const total = summary?.total_buildings ?? 0;
  const candidates = summary?.candidate_buildings ?? 0;
  const below = summary?.below_threshold ?? Math.max(0, total - candidates);
  const threshold = summary?.threshold ?? 3.3;
  return <>
    <div className="kd-welcome-row"><div><div className="kd-eyebrow">GEOSPATIAL INTELLIGENCE PLATFORM</div><h1>Welcome to <em>KERNEL</em></h1><p>Satellite-based Battle Damage Assessment</p></div><div className="kd-welcome-actions"><button className="kd-secondary-btn" onClick={onRefresh} disabled={loading}><RefreshCw size={15}/> Refresh</button></div></div>
    {error && <div className="kd-alert"><AlertTriangle size={17}/>{error}</div>}
    {!summary?.data_available && !loading && <div className="kd-alert"><AlertTriangle size={17}/> No scored building dataset is available. Add the GeoTIFF and GeoJSON files to data/ and run the processing pipeline.</div>}
    <section className="kd-stats-grid">
      <StatCard icon={Building2} label="BUILDINGS SCREENED" value={loading ? '—' : total.toLocaleString()} note="Actual building footprints"/>
      <StatCard icon={AlertTriangle} label="CANDIDATES FOR REVIEW" value={loading ? '—' : candidates.toLocaleString()} note="Mean T-statistic above threshold" tone="amber"/>
      <StatCard icon={Activity} label="SCREENING THRESHOLD" value={`T > ${threshold}`} note="Configurable screening threshold"/>
      <StatCard icon={CalendarDays} label="INFERENCE WINDOW" value={`${config?.post_interval_months ?? 1} month`} note="PWTT processing configuration" tone="violet"/>
    </section>

    <section className="kd-hero-grid">
      <article className="kd-hero-map-card"><div className="kd-map-context"><small><i/> SELECTED AREA OF INTEREST</small><h2>Bakhmut</h2><span>Ukraine</span><p>Primary study area for Sentinel-1 radar change screening.</p><button onClick={() => document.getElementById('kd-overview-map')?.scrollIntoView({behavior:'smooth'})}>View Details <ArrowRight size={14}/></button></div><div className="kd-overview-map" id="kd-overview-map"><DamageMap data={data} onSelect={setSelected} threshold={threshold}/></div><div className="kd-legend"><span><i className="green"/>Below threshold</span><span><i className="amber"/>Flagged for review</span><span><i className="red"/>High change</span></div></article>
      <div className="kd-status-stack"><StatusCard icon={Signal} label="API STATUS" value="Online" detail="FastAPI local service" status/><StatusCard icon={Layers3} label="ACTIVE STUDY AREA" value="Bakhmut, Ukraine" detail="Primary area of interest"/><StatusCard icon={Clock3} label="LAST UPDATED" value={updated || 'Not refreshed'} detail="Local data refresh"/><button className="kd-refresh-card" onClick={onRefresh} disabled={loading}><RefreshCw size={16}/>Refresh analysis data</button></div>
    </section>

    {selected && <section className="kd-panel kd-inline-inspection"><header><div><h2><Building2 size={17}/> Building inspection</h2><p>Selected building-level change indicator</p></div><button className="kd-clear-selection" onClick={() => setSelected(null)}>Clear selection</button></header><div className="kd-inline-metrics"><div><small>Building ID</small><b>#{selected.building_id ?? selected.id ?? '—'}</b></div><div><small>Mean T-statistic</small><b>{selected.mean_t == null ? '—' : Number(selected.mean_t).toFixed(2)}</b></div><div><small>Maximum T-statistic</small><b>{selected.max_t == null ? '—' : Number(selected.max_t).toFixed(2)}</b></div><div><small>Valid pixels</small><b>{selected.valid_pixels ?? '—'}</b></div><div><small>Screening status</small><b className={Number(selected.mean_t) > Number(threshold) ? 'amber-text' : 'green-text'}>{selected.screening_status || (Number(selected.mean_t) > Number(threshold) ? 'Flagged for review' : 'Below threshold')}</b></div></div><p className="kd-inspection-caveat"><ShieldCheck size={15}/> Statistical change is not confirmation of physical damage; analyst verification is required.</p></section>}

    <section className="kd-section"><header><div><h2>Study Areas</h2><p>Areas currently configured in this workspace</p></div><span>1 configured area <ArrowRight size={14}/></span></header><div className="kd-study-grid"><article className="kd-study-card"><div className="kd-study-image"><MapPinned size={29}/></div><div className="kd-study-copy"><b>Bakhmut</b><p>Eastern Ukraine · Urban and industrial study area</p></div><label>PRIMARY AOI</label><button onClick={() => document.getElementById('kd-overview-map')?.scrollIntoView({behavior:'smooth'})}><ArrowRight size={17}/></button></article><article className="kd-study-card kd-study-add"><div className="kd-add-icon"><Plus size={23}/></div><div className="kd-study-copy"><b>Additional study area</b><p>Configure another AOI when its boundary and imagery dates are available.</p></div><label>NOT CONFIGURED</label></article></div></section>

    <section className="kd-bottom-grid"><article className="kd-panel"><header><div><h2>Analysis Activity</h2><p>Current dataset and processing status</p></div><span className="kd-live"><i/>LIVE DATA</span></header><div className="kd-activity-row"><CheckCircle2/><div><b>Building footprints loaded</b><small>{total.toLocaleString()} features available from scored GeoJSON</small></div><label className="loaded">Loaded</label></div><div className="kd-activity-row"><AlertTriangle/><div><b>Change candidates identified</b><small>{candidates.toLocaleString()} buildings exceed screening threshold</small></div><label className="review">Review</label></div><div className="kd-activity-row"><ShieldCheck/><div><b>Human verification required</b><small>PWTT indicators are not confirmed damage labels</small></div><label>Required</label></div></article>
      <article className="kd-panel"><header><div><h2>Quick Statistics</h2><p>Current screening snapshot</p></div></header><div className="kd-quick-stats"><div><Building2/><b>{loading ? '—' : total.toLocaleString()}</b><small>Total buildings</small></div><div><AlertTriangle/><b>{loading ? '—' : candidates.toLocaleString()}</b><small>For review</small></div><div><CheckCircle2/><b>{loading ? '—' : below.toLocaleString()}</b><small>Below threshold</small></div></div><div className="kd-detail-row"><span>Candidate share</span><b>{summary?.candidate_percent ?? 0}%</b></div><div className="kd-detail-row"><span>Inference start</span><b>{config?.inference_start ?? '2024-07-01'}</b></div></article></section>
    {selected && <div className="kd-selection-panel"><BuildingInspection building={selected} threshold={threshold} onClose={() => setSelected(null)}/></div>}
  </>;
}

function NewAssessment({ config, onSubmitted }) {
  const [form, setForm] = useState({
    war_start: config?.war_start || '2022-02-22',
    inference_start: config?.inference_start || '2024-07-01',
    pre_interval: config?.pre_interval_months || 12,
    post_interval: config?.post_interval_months || 1,
    export_scale: 10,
    export_name: `Kernel_Bakhmut_${new Date().toISOString().slice(0,10).replaceAll('-', '')}`,
  });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const update = (key, value) => setForm(old => ({ ...old, [key]: value }));
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError(''); setMessage('');
    try {
      const result = await onSubmitted({
        west: config?.aoi?.west ?? 37.949421,
        south: config?.aoi?.south ?? 48.556181,
        east: config?.aoi?.east ?? 38.043834,
        north: config?.aoi?.north ?? 48.621584,
        ...form,
        pre_interval: Number(form.pre_interval),
        post_interval: Number(form.post_interval),
        export_scale: Number(form.export_scale),
      });
      setMessage(result.message || 'Assessment export submitted to Earth Engine.');
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <section className="kd-page-section"><div className="kd-page-heading-row"><div><div className="kd-eyebrow">ANALYSIS CONFIGURATION</div><h1>New Assessment</h1><p>Submit a PWTT run for the currently configured Bakhmut area.</p></div></div>
    <div className="kd-form-layout"><form className="kd-panel kd-assessment-form" onSubmit={submit}><h2>Assessment parameters</h2><p className="kd-form-intro">The AOI is preconfigured from your working Bakhmut analysis. Change the event and inference periods as needed.</p>
      <div className="kd-form-grid"><label>Event / reference cutoff date<input type="date" value={form.war_start} onChange={e => update('war_start', e.target.value)} required/></label><label>Inference start date<input type="date" value={form.inference_start} onChange={e => update('inference_start', e.target.value)} required/></label><label>Pre-event reference (months)<input type="number" min="1" max="36" value={form.pre_interval} onChange={e => update('pre_interval', e.target.value)} required/></label><label>Post-event inference (months)<input type="number" min="1" max="6" value={form.post_interval} onChange={e => update('post_interval', e.target.value)} required/></label><label>Raster export scale (metres)<select value={form.export_scale} onChange={e => update('export_scale', e.target.value)}><option value="10">10 m (native spacing)</option><option value="20">20 m</option><option value="30">30 m</option></select></label><label>Export task name<input value={form.export_name} onChange={e => update('export_name', e.target.value)} pattern="[A-Za-z0-9_-]{3,60}" required/></label></div>
      <div className="kd-form-note"><ShieldCheck size={17}/> This creates a Google Earth Engine Drive export. It does not automatically verify building damage. After task completion, place the exported raster in data/ and run the scoring script to update the dashboard.</div>
      {message && <div className="kd-success-message"><CheckCircle2 size={17}/>{message}</div>}{error && <div className="kd-alert"><AlertTriangle size={17}/>{error}</div>}
      <button className="kd-primary-btn" type="submit" disabled={busy}>{busy ? 'Submitting to Earth Engine…' : 'Submit PWTT assessment'} <ArrowRight size={16}/></button>
    </form><aside className="kd-panel kd-parameter-summary"><h2>Configured study area</h2><div className="kd-aoi-card"><MapPinned size={22}/><b>Bakhmut, Ukraine</b><small>37.949421°E, 48.556181°N — 38.043834°E, 48.621584°N</small></div><div className="kd-detail-row"><span>Algorithm</span><b>Pixel-Wise T-Test</b></div><div className="kd-detail-row"><span>Satellite</span><b>Sentinel-1 GRD FLOAT</b></div><div className="kd-detail-row"><span>Polarizations</span><b>VV + VH</b></div><div className="kd-detail-row"><span>Speckle filter</span><b>Lee filter</b></div><div className="kd-detail-row"><span>Orbit handling</span><b>Relative-orbit grouped</b></div></aside></div>
  </section>;
}

function DamageAnalysis({ data, summary, onSelectBuilding }) {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const features = data?.features || [];
  const filtered = useMemo(() => features.filter(f => {
    const p = f.properties || {};
    const score = Number(p.mean_t);
    const flagged = p.screening_flag ?? (Number.isFinite(score) && score > Number(summary?.threshold ?? 3.3));
    const matchFilter = filter === 'all' || (filter === 'flagged' ? flagged : !flagged);
    const matchQuery = String(p.building_id ?? f.id ?? '').toLowerCase().includes(query.toLowerCase());
    return matchFilter && matchQuery;
  }), [features, filter, query, summary]);
  return <section className="kd-page-section"><div className="kd-page-heading-row"><div><div className="kd-eyebrow">BUILDING-LEVEL SCREENING</div><h1>Damage Analysis</h1><p>Explore the actual building-level PWTT scores from your scored GeoJSON.</p></div><a className="kd-secondary-btn" href={csvExportUrl}><Download size={15}/>Export CSV</a></div>
    <div className="kd-analysis-summary"><div><small>Total features</small><b>{features.length.toLocaleString()}</b></div><div><small>Flagged for review</small><b>{(summary?.candidate_buildings ?? 0).toLocaleString()}</b></div><div><small>Screening threshold</small><b>T &gt; {summary?.threshold ?? 3.3}</b></div></div>
    <div className="kd-panel kd-table-panel"><div className="kd-table-tools"><label className="kd-search"><Search size={16}/><input placeholder="Search building ID…" value={query} onChange={e => setQuery(e.target.value)}/></label><select value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All buildings</option><option value="flagged">Flagged for review</option><option value="below">Below threshold</option></select><span>{filtered.length.toLocaleString()} results</span></div>
      <div className="kd-table-scroll"><table><thead><tr><th>Building ID</th><th>Mean T</th><th>Maximum T</th><th>Valid pixels</th><th>Screening status</th><th/></tr></thead><tbody>{filtered.slice(0, 250).map((feature, index) => {const p = feature.properties || {}; const flagged = p.screening_flag ?? Number(p.mean_t) > Number(summary?.threshold ?? 3.3); return <tr key={p.building_id ?? feature.id ?? index}><td>#{p.building_id ?? feature.id ?? index + 1}</td><td>{p.mean_t == null ? '—' : Number(p.mean_t).toFixed(2)}</td><td>{p.max_t == null ? '—' : Number(p.max_t).toFixed(2)}</td><td>{p.valid_pixels ?? '—'}</td><td><span className={`kd-status-tag ${flagged ? 'flagged' : 'clear'}`}>{p.screening_status || (flagged ? 'Flagged for review' : 'Below threshold')}</span></td><td><button className="kd-row-button" onClick={() => onSelectBuilding(p)}>Inspect</button></td></tr>;})}</tbody></table></div>
      {filtered.length > 250 && <p className="kd-table-note">Showing the first 250 matches. Export the CSV for the complete dataset.</p>}
      {filtered.length === 0 && <div className="kd-empty-table">No matching buildings.</div>}
    </div>
  </section>;
}

function Reports({ summary, config }) {
  return <section className="kd-page-section"><div className="kd-page-heading-row"><div><div className="kd-eyebrow">EXPORTS & DOCUMENTATION</div><h1>Intelligence Reports</h1><p>Download the current machine-generated screening dataset and review its methodology.</p></div></div>
    <div className="kd-report-grid"><article className="kd-panel kd-report-card"><div className="kd-report-icon"><FileText size={25}/></div><h2>Building screening CSV</h2><p>One row per building, including mean/max T-statistic, valid pixel count and screening status.</p><a className="kd-primary-btn" href={csvExportUrl}><Download size={16}/>Download CSV</a></article><article className="kd-panel kd-report-card"><div className="kd-report-icon"><Activity size={25}/></div><h2>Current analysis summary</h2><p>{(summary?.total_buildings ?? 0).toLocaleString()} buildings screened; {(summary?.candidate_buildings ?? 0).toLocaleString()} currently flagged for analyst review.</p><button className="kd-secondary-btn" onClick={() => window.print()}><FileText size={15}/>Print summary</button></article></div>
    <article className="kd-panel kd-report-method"><h2>Method and interpretation</h2><p>Sentinel-1 GRD FLOAT VV/VH observations are filtered by instrument mode and area, Lee-filtered, log-transformed and analysed with the installed PWTT package. The package calculates separate relative-orbit results and returns a T-statistic image. Building scores are zonal summaries of the exported T-statistic raster.</p><div className="kd-detail-row"><span>Study area</span><b>Bakhmut, Ukraine</b></div><div className="kd-detail-row"><span>War / reference cutoff</span><b>{config?.war_start ?? '2022-02-22'}</b></div><div className="kd-detail-row"><span>Inference period</span><b>{config?.inference_start ?? '2024-07-01'} · one month</b></div><div className="kd-detail-row"><span>Building threshold</span><b>T &gt; {summary?.threshold ?? 3.3}</b></div><div className="kd-form-note"><ShieldCheck size={17}/> These outputs identify statistically unusual change. They are not verified building-damage labels and must not be used as a substitute for field or expert verification.</div></article>
  </section>;
}

export default function App() {
  const [active, setActive] = useState('dashboard');
  const [summary, setSummary] = useState(null);
  const [data, setData] = useState(EMPTY);
  const [config, setConfig] = useState(null);
  const [engineOnline, setEngineOnline] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updated, setUpdated] = useState('');
  const [selected, setSelected] = useState(null);
  const [taskInfo, setTaskInfo] = useState(null);

  async function refresh() {
    setLoading(true); setError('');
    try {
      const [health, s, b, c] = await Promise.all([getHealth(), getSummary(), getBuildings(), getConfig()]);
      setEngineOnline(health.status === 'ok'); setSummary(s); setData(b); setConfig(c);
      setUpdated(new Date().toLocaleString([], { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }));
    } catch (e) { setEngineOnline(false); setError(e.message || 'Could not load backend data.'); }
    finally { setLoading(false); }
  }
  async function handleAssessment(payload) {
    const result = await submitAssessment(payload);
    setTaskInfo(result);
    return result;
  }
  useEffect(() => { refresh(); }, []);

  const titles = {dashboard:'Dashboard',assessment:'New Assessment',comparison:'Satellite Comparison',analysis:'Damage Analysis',reports:'Intelligence Reports'};
  const navigate = (page) => { setActive(page); setSelected(null); };

  return <div className="kd-app"><Sidebar active={active} onNavigate={navigate} engineOnline={engineOnline}/><main className="kd-main"><Topbar title={titles[active]} engineOnline={engineOnline} onRefresh={refresh} loading={loading}/><div className="kd-content">
    {active === 'dashboard' && <Dashboard summary={summary} data={data} config={config} loading={loading} error={error} updated={updated} selected={selected} setSelected={setSelected} onRefresh={refresh}/>}
    {active === 'assessment' && <><NewAssessment config={config} onSubmitted={handleAssessment}/>{taskInfo?.tasks?.length > 0 && <div className="kd-task-inline">Earth Engine task: {taskInfo.tasks.map(t => `${t.description} (${t.state})`).join(', ')}</div>}</>}
    {active === 'comparison' && <SatelliteComparison/>}
    {active === 'analysis' && <DamageAnalysis data={data} summary={summary} onSelectBuilding={(p) => {setSelected(p); setActive('dashboard');}}/>}
    {active === 'reports' && <Reports summary={summary} config={config}/>}
    <footer className="kd-footer"><span>KERNEL · HACKNAUTS 2.0</span><span>Decision-support prototype · Human verification required</span></footer>
  </div></main></div>;
}
