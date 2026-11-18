import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Blocks,
  Building2,
  ChevronRight,
  CircleHelp,
  Command,
  Gauge,
  Sandwich,
  LayoutDashboard,
  LogOut,
  Plus,
  Radio,
  Server,
  ShieldCheck,
  Wifi,
} from 'lucide-react';
import { createAgent, createDns, createIperf, createMtr, createNmap, createPing, createSipp, createSite, createTraceroute, getAgents, getOverview, getSites, getTests, login, revokeAgent } from './api';
import { combos, eligibleSource, isPlainSeasoning, plainSeasoning, placeOrder, tools, type Combo, type Engine } from './burger';
import type { Agent, Overview, Site, TestSession } from './types';

const AgentAvailabilityChart = lazy(() => import('./AgentAvailabilityChart'));

type Page = 'overview' | 'sites' | 'agents' | 'tests';
type Inventory = { overview: Overview; sites: Site[]; agents: Agent[]; tests: TestSession[] };

function App() {
  const [token, setToken] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [page, setPage] = useState<Page>('overview');
  const [testView, setTestView] = useState<'build' | 'bite'>('build');
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [siteName, setSiteName] = useState('');
  const [siteRegion, setSiteRegion] = useState('');
  const [agentName, setAgentName] = useState('');
  const [agentSite, setAgentSite] = useState('');
  const [credential, setCredential] = useState('');
  const [sourceAgent, setSourceAgent] = useState('');
  const [target, setTarget] = useState('');
  const [cycles, setCycles] = useState(plainSeasoning.cycles);
  const [engines, setEngines] = useState<Engine[]>(['mtr']);
  const [ordering, setOrdering] = useState(false);
  const [orderNotice, setOrderNotice] = useState('');
  const [orderError, setOrderError] = useState('');
  const orderInFlight = useRef(false);
  const [scanPorts, setScanPorts] = useState(plainSeasoning.scanPorts);
  const [pingCount, setPingCount] = useState(plainSeasoning.pingCount);
  const [dnsServer, setDnsServer] = useState(plainSeasoning.dnsServer);
  const [dnsType, setDnsType] = useState(plainSeasoning.dnsType);
  const [destinationAgent, setDestinationAgent] = useState(plainSeasoning.destinationAgent);
  const [iperfPort, setIperfPort] = useState(plainSeasoning.iperfPort);
  const [duration, setDuration] = useState(plainSeasoning.duration);
  const [sipPort, setSipPort] = useState(plainSeasoning.sipPort);
  const [service, setService] = useState(plainSeasoning.service);
  const [calls, setCalls] = useState(plainSeasoning.calls);
  const [rate, setRate] = useState(plainSeasoning.rate);
  const [concurrency, setConcurrency] = useState(plainSeasoning.concurrency);
  const [maxHops, setMaxHops] = useState(plainSeasoning.maxHops);

  const refresh = useCallback(async (accessToken: string) => {
    setLoading(true);
    setError('');
    try {
      const [overview, sites, agents, tests] = await Promise.all([
        getOverview(accessToken),
        getSites(accessToken),
        getAgents(accessToken),
        getTests(accessToken),
      ]);
      setInventory({ overview, sites, agents, tests });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not load inventory');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) void refresh(token);
  }, [token, refresh]);

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await login(username, password);
      setPassword('');
      setToken(response.access_token);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Sign in failed');
      setLoading(false);
    }
  }

  async function handleCreateSite(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !siteName.trim()) return;
    setError('');
    try {
      await createSite(token, { name: siteName.trim(), region: siteRegion.trim() || null, category: null });
      setSiteName('');
      setSiteRegion('');
      await refresh(token);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not create site');
    }
  }

  async function handleCreateAgent(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setCredential('');
    try {
      const result = await createAgent(token, agentName.trim(), agentSite || null);
      setCredential(result.credential);
      setAgentName('');
      await refresh(token);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not register chef');
    }
  }

  async function handleCreateTest(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (orderInFlight.current) return;
    setError('');
    setOrderNotice('');
    setOrderError('');
    if (!engines.length) {
      setError('Choose at least one tool patty.');
      return;
    }
    const source = inventory?.agents.find((agent) => agent.id === sourceAgent);
    if (!source || source.status !== 'online' || !eligibleSource(engines, source.available_engines)) {
      setError('Choose an online chef that supports every selected tool.');
      return;
    }
    const parts = scanPorts.split(',').map((part) => part.trim());
    const ports = parts.map(Number);
    if (engines.includes('nmap') && (parts.some((part) => !/^\d+$/.test(part)) || ports.length > 100 || ports.some((port) => port < 1 || port > 65535) || new Set(ports).size !== ports.length)) {
      setError('Enter 1–100 distinct TCP ports from 1 to 65535, separated by commas.');
      return;
    }
    orderInFlight.current = true;
    setOrdering(true);
    try {
      const result = await placeOrder(engines, async (engine) => {
        if (engine === 'mtr') {
          await createMtr(token, sourceAgent, target.trim(), cycles);
        } else if (engine === 'iperf3') {
          await createIperf(token, { source_agent_id: sourceAgent, destination_agent_id: destinationAgent || null, target: target.trim(), port: iperfPort, duration });
        } else if (engine === 'sipp') {
          await createSipp(token, { source_agent_id: sourceAgent, target: target.trim(), port: sipPort, service, calls, rate, concurrency });
        } else if (engine === 'nmap') {
          await createNmap(token, sourceAgent, target.trim(), ports);
        } else if (engine === 'ping') {
          await createPing(token, sourceAgent, target.trim(), pingCount);
        } else if (engine === 'dns') {
          await createDns(token, sourceAgent, target.trim(), dnsServer.trim(), dnsType);
        } else {
          await createTraceroute(token, sourceAgent, target.trim(), maxHops);
        }
      });
      await refresh(token);
      if (result.queued.length) {
        setOrderNotice(`Order placed: ${result.queued.map((engine) => tools.find((tool) => tool.id === engine)?.name).join(', ')} queued. Take a bite to see each test's status and report.`);
      }
      if (result.failed.length) {
        setEngines(result.failed.map((item) => item.engine));
        setOrderError(`Not confirmed: ${result.failed.map((item) => `${item.engine.toUpperCase()} (${item.error})`).join('; ')}. Only unconfirmed tools remain selected. Check recent tests before retrying: a lost response may mean a test was queued.`);
      }
    } finally {
      orderInFlight.current = false;
      setOrdering(false);
    }
  }

  function chooseEngines(next: Engine[]) {
    setEngines(next);
    setOrderNotice('');
    if (next.length && !eligibleSource(next, inventory?.agents.find((agent) => agent.id === sourceAgent)?.available_engines ?? [])) {
      setSourceAgent('');
      setDestinationAgent('');
    }
  }

  function chooseCombo(combo: Combo) {
    setCycles(plainSeasoning.cycles);
    setScanPorts(plainSeasoning.scanPorts);
    setPingCount(plainSeasoning.pingCount);
    setDnsServer(plainSeasoning.dnsServer);
    setDnsType(plainSeasoning.dnsType);
    setDestinationAgent(plainSeasoning.destinationAgent);
    setIperfPort(plainSeasoning.iperfPort);
    setDuration(plainSeasoning.duration);
    setSipPort(plainSeasoning.sipPort);
    setService(plainSeasoning.service);
    setCalls(plainSeasoning.calls);
    setRate(plainSeasoning.rate);
    setConcurrency(plainSeasoning.concurrency);
    setMaxHops(plainSeasoning.maxHops);
    if (combo.settings.cycles !== undefined) setCycles(combo.settings.cycles);
    if (combo.settings.pingCount !== undefined) setPingCount(combo.settings.pingCount);
    if (combo.settings.scanPorts !== undefined) setScanPorts(combo.settings.scanPorts);
    chooseEngines([...combo.engines]);
  }

  function resetSeasoning(engine: Engine) {
    if (engine === 'mtr') setCycles(plainSeasoning.cycles);
    else if (engine === 'ping') setPingCount(plainSeasoning.pingCount);
    else if (engine === 'traceroute') setMaxHops(plainSeasoning.maxHops);
    else if (engine === 'dns') {
      setDnsServer(plainSeasoning.dnsServer);
      setDnsType(plainSeasoning.dnsType);
    } else if (engine === 'nmap') setScanPorts(plainSeasoning.scanPorts);
    else if (engine === 'iperf3') {
      setDestinationAgent(plainSeasoning.destinationAgent);
      setIperfPort(plainSeasoning.iperfPort);
      setDuration(plainSeasoning.duration);
    } else {
      setSipPort(plainSeasoning.sipPort);
      setService(plainSeasoning.service);
      setCalls(plainSeasoning.calls);
      setRate(plainSeasoning.rate);
      setConcurrency(plainSeasoning.concurrency);
    }
  }

  async function handleRevokeAgent(agent: Agent) {
    if (!window.confirm(`Revoke ${agent.name}? Its queued and running tests will be cancelled.`)) return;
    setError('');
    try {
      await revokeAgent(token, agent.id);
      setCredential('');
      await refresh(token);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not revoke chef');
    }
  }

  if (!token) {
    return (
      <main className="login-shell">
        <div className="login-card">
          <div className="brand-mark"><Sandwich size={23} /></div>
          <p className="eyebrow">NETWORK OPERATIONS</p>
          <h1>Welcome back</h1>
          <p className="muted">Welcome to the brgrByte Order Window.</p>
          <form onSubmit={handleLogin} className="login-form">
            <label htmlFor="username">Username</label>
            <input id="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required />
            <label htmlFor="password">Password</label>
            <input id="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            {error && <p className="error-message" role="alert">{error}</p>}
            <button className="primary-button full-width" type="submit" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in'} <ChevronRight size={17} />
            </button>
          </form>
          <div className="secure-note"><ShieldCheck size={15} /> Authenticated control dashboard</div>
        </div>
      </main>
    );
  }

  const overview = inventory?.overview;
  const agents = inventory?.agents ?? [];
  const sites = inventory?.sites ?? [];
  const onlineCount = overview?.online_agents ?? 0;
  const offlineCount = Math.max(0, (overview?.total_agents ?? 0) - onlineCount);
  const pageTitle = page === 'overview' ? 'Overview' : page === 'sites' ? 'Sites' : page === 'agents' ? 'Chefs' : 'Build & bite';
  const seasoning = {
    cycles, pingCount, scanPorts, dnsServer, dnsType, destinationAgent,
    iperfPort, duration, sipPort, service, calls, rate, concurrency, maxHops,
  };
  const isPlain = (engine: Engine) => isPlainSeasoning(engine, seasoning);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark small"><Sandwich size={18} /></div>
          <span>Brgr<span className="brand-light">Byte</span></span>
          <span className="version-pill">0.1</span>
        </div>
        <div className="workspace-label">WORKSPACE</div>
        <div className="workspace-switch"><div className="workspace-icon"><Command size={17} /></div><div><strong>Order Window</strong><small>Control dashboard</small></div><ChevronRight size={15} className="workspace-chevron" /></div>
        <div className="nav-section">MONITORING</div>
        <nav className="nav-list" aria-label="Main navigation">
          <button className={`nav-item ${page === 'overview' ? 'active' : ''}`} onClick={() => setPage('overview')}><LayoutDashboard size={17} /> Overview</button>
          <button className={`nav-item ${page === 'sites' ? 'active' : ''}`} onClick={() => setPage('sites')}><Building2 size={17} /> Sites <span className="nav-count">{sites.length}</span></button>
          <button className={`nav-item ${page === 'agents' ? 'active' : ''}`} onClick={() => setPage('agents')}><Server size={17} /> Chefs <span className="nav-count">{agents.length}</span></button>
          <button className={`nav-item ${page === 'tests' ? 'active' : ''}`} aria-label="Build & bite: tests and reports" onClick={() => setPage('tests')}><Sandwich size={17} /> Build & bite</button>
        </nav>
        <div className="sidebar-bottom">
          <div className="help-card"><CircleHelp size={17} /><div><strong>Getting started</strong><small>Add your first chef</small></div><ChevronRight size={14} /></div>
          <button className="user-profile" onClick={() => { setToken(''); setInventory(null); setCredential(''); setOrderNotice(''); setOrderError(''); setTestView('build'); setPage('overview'); }}>
            <span className="avatar">{username.slice(0, 1).toUpperCase() || 'A'}</span><span className="user-copy"><strong>{username}</strong><small>Administrator</small></span><LogOut size={15} />
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumbs"><span>brgrByte</span><ChevronRight size={14} /><strong>{pageTitle}</strong></div>
          <div className="topbar-actions"><span className="system-status"><i /> Order Window operational</span><button className="icon-button" aria-label="Refresh data" onClick={() => void refresh(token)} disabled={loading}><Activity size={17} /></button></div>
        </header>
        <div className="page-content">
          <p className="tool-attribution">brgrByte wraps independent network tools and uses the <a href="https://nmap.org/" target="_blank" rel="noopener noreferrer">Nmap Security Scanner</a> for TCP scans.</p>
          <div className="page-heading">
            <div><p className="eyebrow">NETWORK OPERATIONS</p><h1>{pageTitle}</h1><p className="muted">{page === 'overview' ? 'A live view of your distributed testing infrastructure.' : page === 'sites' ? 'Manage locations across your network.' : page === 'agents' ? 'Manage chefs, their connections, and available tools.' : 'Order tests by choosing patties and seasoning; then take a bite of the results.'}</p></div>
            {page === 'sites' && <button className="primary-button" onClick={() => document.getElementById('site-name')?.focus()}><Plus size={16} /> Add site</button>}
          </div>

          {error && <div className="banner-error" role="alert">{error}</div>}
          {loading && !inventory ? <div className="loading-state"><div className="spinner" /> Loading control-center data…</div> : null}
          {inventory && page === 'overview' && (
            <>
              <section className="stat-grid" aria-label="Network summary">
                <StatCard icon={<Building2 size={18} />} label="Total sites" value={overview?.total_sites ?? 0} caption="Configured locations" tone="blue" />
                <StatCard icon={<Server size={18} />} label="Chefs" value={overview?.total_agents ?? 0} caption={`${onlineCount} currently online`} tone="violet" />
                <StatCard icon={<Wifi size={18} />} label="Online chefs" value={onlineCount} caption={offlineCount ? `${offlineCount} offline` : 'All systems reachable'} tone="green" />
                <StatCard icon={<Gauge size={18} />} label="Active tests" value={overview?.active_tests ?? 0} caption="Currently executing" tone="amber" />
              </section>
              <section className="content-grid">
                <article className="panel health-panel">
                  <PanelHeading title="Chef availability" subtitle="Current connectivity across your sites" icon={<Radio size={17} />} />
                  {agents.length ? <Suspense fallback={<div className="loading-state">Loading chart…</div>}><AgentAvailabilityChart onlineCount={onlineCount} offlineCount={offlineCount} totalCount={agents.length} /></Suspense> : <EmptyState icon={<Server size={22} />} title="No chefs connected" description="Once chefs register, their availability will appear here." />}
                </article>
                <article className="panel activity-panel">
                  <PanelHeading title="Recent activity" subtitle="Latest chef updates" icon={<Activity size={17} />} />
                  {agents.length ? <div className="activity-list">{agents.slice(0, 5).map((agent) => <AgentRow key={agent.id} agent={agent} siteName={sites.find((site) => site.id === agent.site_id)?.name ?? 'Unassigned'} />)}</div> : <EmptyState icon={<Blocks size={22} />} title="Nothing to report yet" description="Chef status and test activity will show up here." />}
                </article>
              </section>
              <article className="panel trend-panel">
                <PanelHeading title="Network health" subtitle="Historical test measurements" icon={<Activity size={17} />} />
                {inventory.tests.length ? <EmptyState icon={<Gauge size={22} />} title={`${inventory.tests.length} recent test sessions`} description="Open Build & bite to view their status and measurements." /> : <EmptyState icon={<Gauge size={22} />} title="No test results yet" description="Build a burger and run a test to collect measurements." />}
              </article>
            </>
          )}

          {inventory && page === 'sites' && (
            <section className="inventory-layout">
              <article className="panel table-panel">
                <PanelHeading title="Locations" subtitle={`${sites.length} configured ${sites.length === 1 ? 'site' : 'sites'}`} icon={<Building2 size={17} />} />
                {sites.length ? <div className="table-scroll"><table><thead><tr><th>SITE</th><th>REGION</th><th>CATEGORY</th><th>CHEFS</th></tr></thead><tbody>{sites.map((site) => <tr key={site.id}><td><strong>{site.name}</strong></td><td>{site.region || '—'}</td><td>{site.category || '—'}</td><td>{agents.filter((agent) => agent.site_id === site.id).length}</td></tr>)}</tbody></table></div> : <EmptyState icon={<Building2 size={22} />} title="No sites created" description="Create a site to organize your chefs." />}
              </article>
              <article className="panel create-panel">
                <PanelHeading title="Add a site" subtitle="Create a network location" icon={<Plus size={17} />} />
                <form className="site-form" onSubmit={(event) => void handleCreateSite(event)}><label htmlFor="site-name">Site name</label><input id="site-name" value={siteName} onChange={(event) => setSiteName(event.target.value)} placeholder="e.g. pi-dc-lab" maxLength={120} required /><label htmlFor="site-region">Region <span>Optional</span></label><input id="site-region" value={siteRegion} onChange={(event) => setSiteRegion(event.target.value)} placeholder="e.g. West" maxLength={120} /><button className="primary-button" type="submit"><Plus size={16} /> Create site</button></form>
              </article>
            </section>
          )}

          {inventory && page === 'agents' && (
            <section className="inventory-layout"><article className="panel table-panel">
              <PanelHeading title="Chefs" subtitle={`${agents.length} registered ${agents.length === 1 ? 'chef' : 'chefs'}`} icon={<Server size={17} />} />
              {agents.length ? <div className="table-scroll"><table><thead><tr><th>CHEF</th><th>SITE</th><th>STATUS</th><th>PLATFORM</th><th>LAST SEEN</th><th>TOOLS</th><th>ACTION</th></tr></thead><tbody>{agents.map((agent) => <tr key={agent.id}><td><strong>{agent.name}</strong><small className="cell-subtitle">{agent.hostname ?? 'Hostname unavailable'}</small></td><td>{sites.find((site) => site.id === agent.site_id)?.name ?? 'Unassigned'}</td><td><StatusBadge status={agent.status} /></td><td>{[agent.os_name, agent.architecture].filter(Boolean).join(' · ') || '—'}</td><td>{agent.last_seen_at ? new Date(agent.last_seen_at).toLocaleString() : 'Never'}</td><td>{agent.available_engines.length ? agent.available_engines.join(', ') : '—'}</td><td><button onClick={() => void handleRevokeAgent(agent)}>Revoke</button></td></tr>)}</tbody></table></div> : <EmptyState icon={<Server size={22} />} title="No chefs yet" description="Register a chef here, then install its site agent." />}
            </article><article className="panel create-panel">
              <PanelHeading title="Add a chef" subtitle="Register a site agent · Administrator only" icon={<Plus size={17} />} />
              <form className="site-form" onSubmit={(event) => void handleCreateAgent(event)}>
                <label htmlFor="agent-name">Chef name</label><input id="agent-name" value={agentName} onChange={(event) => setAgentName(event.target.value)} maxLength={120} required />
                <label htmlFor="agent-site">Site (optional)</label><select id="agent-site" value={agentSite} onChange={(event) => setAgentSite(event.target.value)}><option value="">Unassigned</option>{sites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}</select>
                <button className="primary-button" type="submit">Add chef</button>
              </form>
              {credential && <p role="status">Copy this credential now; it will not be shown again: <code style={{ overflowWrap: 'anywhere' }}>{credential}</code></p>}
            </article></section>
          )}

          {inventory && page === 'tests' && (
            <section className="burger-workspace">
              <div className="burger-steps" aria-label="Test workflow">
                <button type="button" className={testView === 'build' ? 'active' : ''} aria-pressed={testView === 'build'} onClick={() => setTestView('build')}><span>1</span> Build your burger <small>Choose tests</small></button>
                <button type="button" className={testView === 'bite' ? 'active' : ''} aria-pressed={testView === 'bite'} onClick={() => { setTestView('bite'); void refresh(token); }}><span>2</span> Take a bite <small>View results</small></button>
              </div>
              {orderNotice && <p className="order-notice" role="status">{orderNotice}</p>}
              {orderError && <p className="banner-error" role="alert">{orderError}</p>}
              {testView === 'bite' && <article className="panel table-panel">
                <PanelHeading title="Take a bite: test results" subtitle="Recent tests from all burgers, not grouped by order; refresh to update (last 100)" icon={<Gauge size={17} />} />
                {inventory.tests.length ? inventory.tests.map((test) => <div className="agent-row" key={test.id} style={{ display: 'block' }}>
                  <strong>{test.engine.toUpperCase()} to {test.configuration.target}</strong> — {test.status}
                  <p>{agents.find((agent) => agent.id === test.source_agent_id)?.name ?? 'Unknown chef'} · {new Date(test.created_at).toLocaleString()}</p>
                  {test.results.map((result, index) => <div key={index}><p>{result.agent_id === test.destination_agent_id ? 'Receiver' : 'Source'} result</p>{result.error && <p role="alert">{result.error}</p>}{result.metrics.report !== undefined && (test.engine === 'mtr' ? <MtrReport report={result.metrics.report} /> : <ToolReport engine={test.engine} report={result.metrics.report} />)}</div>)}
                </div>) : <EmptyState icon={<Gauge size={22} />} title="No test results yet" description="Build your burger and run tests to collect reports." />}
              </article>}
              {testView === 'build' && <article className="panel create-panel">
                <PanelHeading title="Build your burger" subtitle="You're the customer: choose your patties, season them, and place your order. Only test authorized systems." icon={<Sandwich size={17} />} />
                <form className="site-form" onSubmit={(event) => void handleCreateTest(event)}>
                  <fieldset className="order-fields" disabled={ordering}>
                  <div className="burger-hero"><div className="burger-illustration" aria-hidden="true"><span className="bun-top" /><span className="lettuce" />{engines.map((engine) => <span className="patty" key={engine} />)}<span className="cheese" /><span className="bun-bottom" /></div><div><strong>{engines.length} {engines.length === 1 ? 'patty' : 'patties'}</strong><p>Choose tools as patties, then adjust each patty's seasoning.</p></div></div>
                  <p className="order-label">COMBOS <span>Presets replace selected patties and seasonings.</span></p>
                  <div className="combo-grid">{combos.map((combo) => <button className="combo-button" type="button" key={combo.name} onClick={() => chooseCombo(combo)}><strong>{combo.name}</strong><small>{combo.description}</small></button>)}</div>
                  <fieldset className="tool-selector"><legend>Pick your patties <span>Tools</span></legend><div className="tool-grid">{tools.map((tool) => <label className={`tool-choice ${engines.includes(tool.id) ? 'selected' : ''}`} key={tool.id}><input type="checkbox" checked={engines.includes(tool.id)} onChange={(event) => chooseEngines(event.target.checked ? [...engines, tool.id] : engines.filter((engine) => engine !== tool.id))} /><span><strong>{tool.name}</strong><small>{tool.description}</small></span></label>)}</div></fieldset>
                  <label htmlFor="source-agent">Choose your chef <span>Must support every selected patty</span></label><select id="source-agent" value={sourceAgent} onChange={(event) => { setSourceAgent(event.target.value); setDestinationAgent(''); }} required><option value="">Select a chef</option>{agents.filter((agent) => agent.status === 'online' && eligibleSource(engines, agent.available_engines)).map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}</select>
                  <label htmlFor="target">Destination hostname or IP {engines.includes('dns') && <span>(DNS query name for DNS)</span>}</label><input id="target" value={target} onChange={(event) => setTarget(event.target.value)} maxLength={253} required />
                  <p className="order-label">SEASON YOUR PATTIES <span>Plain keeps each tool's default settings</span></p>
                  {engines.includes('mtr') && <SeasoningPanel name="MTR" plain={isPlain('mtr')} onReset={() => resetSeasoning('mtr')}><label htmlFor="cycles">Probe cycles (1–20)</label><input id="cycles" type="number" min={1} max={20} value={cycles} onChange={(event) => setCycles(Number(event.target.value))} required /></SeasoningPanel>}
                  {engines.includes('nmap') && <SeasoningPanel name="Nmap" plain={isPlain('nmap')} onReset={() => resetSeasoning('nmap')}><p>TCP connect scan of one authorized host using the <a href="https://nmap.org/" target="_blank" rel="noopener noreferrer">Nmap Security Scanner</a>. Results can be affected by firewalls; no service version detection is performed.</p><label htmlFor="scan-ports">TCP ports (1–100 comma-separated numbers)</label><input id="scan-ports" value={scanPorts} onChange={(event) => setScanPorts(event.target.value)} required /></SeasoningPanel>}
                  {engines.includes('ping') && <SeasoningPanel name="Ping" plain={isPlain('ping')} onReset={() => resetSeasoning('ping')}><label htmlFor="ping-count">ICMP probes (1–10)</label><input id="ping-count" type="number" min={1} max={10} value={pingCount} onChange={(event) => setPingCount(Number(event.target.value))} required /></SeasoningPanel>}
                  {engines.includes('traceroute') && <SeasoningPanel name="Traceroute" plain={isPlain('traceroute')} onReset={() => resetSeasoning('traceroute')}><p>UDP traceroute. Firewalls may block probes or replies.</p><label htmlFor="max-hops">Maximum hops (1–30)</label><input id="max-hops" type="number" min={1} max={30} value={maxHops} onChange={(event) => setMaxHops(Number(event.target.value))} required /></SeasoningPanel>}
                  {engines.includes('dns') && <SeasoningPanel name="DNS" plain={isPlain('dns')} onReset={() => resetSeasoning('dns')}><p>Other tools use the chef's system resolver, not this server.</p><label htmlFor="dns-server">DNS server IPv4 or IPv6 address</label><input id="dns-server" value={dnsServer} onChange={(event) => setDnsServer(event.target.value)} maxLength={45} required /><label htmlFor="dns-type">DNS record type</label><select id="dns-type" value={dnsType} onChange={(event) => setDnsType(event.target.value)}>{['A', 'AAAA', 'CNAME', 'MX', 'NS', 'SOA', 'TXT'].map((type) => <option key={type} value={type}>{type}</option>)}</select></SeasoningPanel>}
                  {engines.includes('iperf3') && <SeasoningPanel name="iPerf3" plain={isPlain('iperf3')} onReset={() => resetSeasoning('iperf3')}><p>iPerf3 may saturate the network link. Managed receivers are unauthenticated; restrict access to the selected port.</p><label htmlFor="destination-agent">Receiver</label><select id="destination-agent" value={destinationAgent} onChange={(event) => setDestinationAgent(event.target.value)}><option value="">External iPerf3 server</option>{agents.filter((agent) => agent.id !== sourceAgent && agent.status === 'online' && agent.available_engines.includes('iperf3')).map((agent) => <option key={agent.id} value={agent.id}>{agent.name} (chef)</option>)}</select><label htmlFor="iperf-port">Receiver TCP port</label><input id="iperf-port" type="number" min={1024} max={65535} value={iperfPort} onChange={(event) => setIperfPort(Number(event.target.value))} required /><label htmlFor="duration">Duration in seconds (1–60)</label><input id="duration" type="number" min={1} max={60} value={duration} onChange={(event) => setDuration(Number(event.target.value))} required /></SeasoningPanel>}
                  {engines.includes('sipp') && <SeasoningPanel name="SIPp" plain={isPlain('sipp')} onReset={() => resetSeasoning('sipp')}><p>SIPp stops after 80 seconds; configure the call count and rate accordingly.</p><label htmlFor="sip-port">SIP UDP port</label><input id="sip-port" type="number" min={1} max={65535} value={sipPort} onChange={(event) => setSipPort(Number(event.target.value))} required /><label htmlFor="service">SIP request URI user</label><input id="service" value={service} onChange={(event) => setService(event.target.value)} maxLength={64} required /><label htmlFor="calls">Total calls (1–1000)</label><input id="calls" type="number" min={1} max={1000} value={calls} onChange={(event) => setCalls(Number(event.target.value))} required /><label htmlFor="rate">Call rate per second (1–20)</label><input id="rate" type="number" min={1} max={20} value={rate} onChange={(event) => setRate(Number(event.target.value))} required /><label htmlFor="concurrency">Maximum concurrent calls (1–100)</label><input id="concurrency" type="number" min={1} max={100} value={concurrency} onChange={(event) => setConcurrency(Number(event.target.value))} required /></SeasoningPanel>}
                  <p className="order-help">Tests share this source and destination, but are queued and reported separately. Long orders can cause queued tests to expire after five minutes.</p>
                  <button className="primary-button order-button" type="submit" disabled={!engines.length}><Sandwich size={16} /> {ordering ? 'Placing order…' : `Place order (${engines.length})`}</button>
                  <button className="bite-button" type="button" onClick={() => { setTestView('bite'); void refresh(token); }}>Take a bite: view results</button>
                  </fieldset>
                </form>
              </article>}
            </section>
          )}
        </div>
      </main>
    </div>
  );
}

function SeasoningPanel({ name, plain, onReset, children }: { name: string; plain: boolean; onReset: () => void; children: React.ReactNode }) {
  return (
    <details className="seasoning-panel">
      <summary>
        <span className="seasoning-title"><strong>{name}</strong><small>Seasoning</small></span>
        <span className={`seasoning-badge ${plain ? 'plain' : 'custom'}`}>{plain ? 'Plain' : 'Seasoned'}</span>
      </summary>
      <div className="topping">
        {children}
        {!plain && <button className="reset-seasoning" type="button" onClick={onReset}>Reset to plain</button>}
      </div>
    </details>
  );
}

function StatCard({ icon, label, value, caption, tone }: { icon: React.ReactNode; label: string; value: number; caption: string; tone: string }) {
  const isOnlineChef = label === 'Online chefs';
  const iconForCaption = isOnlineChef ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />;
  return <article className="stat-card"><div className="stat-top"><div className={`stat-icon ${tone}`}>{icon}</div><span className="stat-label">{label}</span></div><div className="stat-value">{value}</div><div className="stat-caption">{isOnlineChef && value > 0 ? <span className="positive-caption">{iconForCaption}</span> : null}{caption}</div></article>;
}

function PanelHeading({ title, subtitle, icon }: { title: string; subtitle: string; icon: React.ReactNode }) {
  return <div className="panel-heading"><div className="panel-icon">{icon}</div><div><h2>{title}</h2><p>{subtitle}</p></div></div>;
}

function EmptyState({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return <div className="empty-state"><div className="empty-icon">{icon}</div><strong>{title}</strong><p>{description}</p></div>;
}

function StatusBadge({ status }: { status: Agent['status'] }) {
  return <span className={`status-badge ${status}`}><i />{status}</span>;
}

function AgentRow({ agent, siteName }: { agent: Agent; siteName: string }) {
  return <div className="agent-row"><div className={`agent-avatar ${agent.status}`}><Server size={16} /></div><div className="agent-info"><strong>{agent.name}</strong><small>{siteName}</small></div><StatusBadge status={agent.status} /></div>;
}

function MtrReport({ report }: { report: unknown }) {
  const outer = report && typeof report === 'object' && 'report' in report ? report.report : null;
  const hops = outer && typeof outer === 'object' && 'hubs' in outer && Array.isArray(outer.hubs) ? outer.hubs : [];
  const display = (hop: Record<string, unknown>, key: string) => {
    const value = hop[key];
    return typeof value === 'string' || typeof value === 'number' ? value : '—';
  };
  return <div>
    <div className="table-scroll"><table><thead><tr><th>HOP</th><th>HOST</th><th>LOSS %</th><th>SENT</th><th>LAST MS</th><th>AVG MS</th><th>BEST MS</th><th>WORST MS</th></tr></thead><tbody>{hops.filter((hop): hop is Record<string, unknown> => !!hop && typeof hop === 'object').map((hop, index) => <tr key={index}><td>{display(hop, 'count')}</td><td>{display(hop, 'host')}</td><td>{display(hop, 'Loss%')}</td><td>{display(hop, 'Snt')}</td><td>{display(hop, 'Last')}</td><td>{display(hop, 'Avg')}</td><td>{display(hop, 'Best')}</td><td>{display(hop, 'Wrst')}</td></tr>)}</tbody></table></div>
    <details><summary>View raw JSON</summary><pre style={{ overflowX: 'auto', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(report, null, 2)}</pre></details>
  </div>;
}

function ToolReport({ engine, report }: { engine: string; report: unknown }) {
  const data = report && typeof report === 'object' ? report as Record<string, unknown> : {};
  const end = data.end && typeof data.end === 'object' ? data.end as Record<string, unknown> : {};
  const received = end.sum_received && typeof end.sum_received === 'object' ? end.sum_received as Record<string, unknown> : {};
  return <div>
    {engine === 'iperf3' && typeof received.bits_per_second === 'number' && <p>Receiver throughput: {(received.bits_per_second / 1_000_000).toFixed(2)} Mbps</p>}
    {engine === 'sipp' && <p>Successful calls: {String(data.successful_calls ?? '—')} · Failed calls: {String(data.failed_calls ?? '—')}</p>}
    {engine === 'dns' && <><p>DNS server: {String(data.server ?? '—')} · Record type: {String(data.record_type ?? '—')} · Response: {String(data.status ?? '—')} · Answer records: {String(data.answer_count ?? '—')}</p>{data.answer_count === 0 && <p>No answer records were returned; a successful response does not imply the requested record exists.</p>}{typeof data.output === 'string' && <pre style={{ overflowX: 'auto', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{data.output}</pre>}</>}
    {engine === 'nmap' && <><p>Scanned address: {Array.isArray(data.addresses) ? data.addresses.join(', ') : '—'}</p><div className="table-scroll"><table><thead><tr><th>PORT</th><th>STATE</th><th>SERVICE (GUESS)</th></tr></thead><tbody>{Array.isArray(data.ports) && data.ports.filter((port): port is Record<string, unknown> => !!port && typeof port === 'object').map((port, index) => <tr key={index}><td>{String(port.port ?? '—')}/tcp</td><td>{String(port.state ?? '—')}</td><td>{String(port.service ?? '—')}</td></tr>)}</tbody></table></div>{Array.isArray(data.other_ports) && data.other_ports.filter((group): group is Record<string, unknown> => !!group && typeof group === 'object').map((group, index) => <p key={index}>{String(group.count ?? '—')} other ports: {String(group.state ?? '—')}</p>)}</>}
    {(engine === 'ping' || engine === 'traceroute') && typeof data.output === 'string' && <pre style={{ overflowX: 'auto', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{data.output}</pre>}
    <details><summary>View raw JSON</summary><pre style={{ overflowX: 'auto', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(report, null, 2)}</pre></details>
  </div>;
}

export default App;
