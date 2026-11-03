import { lazy, Suspense, useCallback, useEffect, useState } from 'react';
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
  LayoutDashboard,
  LogOut,
  Plus,
  Radio,
  Server,
  ShieldCheck,
  Wifi,
} from 'lucide-react';
import { createSite, getAgents, getOverview, getSites, login } from './api';
import type { Agent, Overview, Site } from './types';

const AgentAvailabilityChart = lazy(() => import('./AgentAvailabilityChart'));

type Page = 'overview' | 'sites' | 'agents';
type Inventory = { overview: Overview; sites: Site[]; agents: Agent[] };

function App() {
  const [token, setToken] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [page, setPage] = useState<Page>('overview');
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [siteName, setSiteName] = useState('');
  const [siteRegion, setSiteRegion] = useState('');

  const refresh = useCallback(async (accessToken: string) => {
    setLoading(true);
    setError('');
    try {
      const [overview, sites, agents] = await Promise.all([
        getOverview(accessToken),
        getSites(accessToken),
        getAgents(accessToken),
      ]);
      setInventory({ overview, sites, agents });
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

  if (!token) {
    return (
      <main className="login-shell">
        <div className="login-card">
          <div className="brand-mark"><Activity size={21} /></div>
          <p className="eyebrow">NETWORK OPERATIONS</p>
          <h1>Welcome back</h1>
          <p className="muted">Sign in to your NetworkPath control center.</p>
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
          <div className="secure-note"><ShieldCheck size={15} /> Authenticated control center</div>
        </div>
      </main>
    );
  }

  const overview = inventory?.overview;
  const agents = inventory?.agents ?? [];
  const sites = inventory?.sites ?? [];
  const onlineCount = overview?.online_agents ?? 0;
  const offlineCount = Math.max(0, (overview?.total_agents ?? 0) - onlineCount);
  const pageTitle = page === 'overview' ? 'Overview' : page === 'sites' ? 'Sites' : 'Agents';

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark small"><Activity size={18} /></div>
          <span>network<span className="brand-light">path</span></span>
          <span className="version-pill">0.1</span>
        </div>
        <div className="workspace-label">WORKSPACE</div>
        <div className="workspace-switch"><div className="workspace-icon"><Command size={17} /></div><div><strong>Control center</strong><small>Network operations</small></div><ChevronRight size={15} className="workspace-chevron" /></div>
        <div className="nav-section">MONITORING</div>
        <nav className="nav-list" aria-label="Main navigation">
          <button className={`nav-item ${page === 'overview' ? 'active' : ''}`} onClick={() => setPage('overview')}><LayoutDashboard size={17} /> Overview</button>
          <button className={`nav-item ${page === 'sites' ? 'active' : ''}`} onClick={() => setPage('sites')}><Building2 size={17} /> Sites <span className="nav-count">{sites.length}</span></button>
          <button className={`nav-item ${page === 'agents' ? 'active' : ''}`} onClick={() => setPage('agents')}><Server size={17} /> Agents <span className="nav-count">{agents.length}</span></button>
        </nav>
        <div className="sidebar-bottom">
          <div className="help-card"><CircleHelp size={17} /><div><strong>Getting started</strong><small>Connect your first agent</small></div><ChevronRight size={14} /></div>
          <button className="user-profile" onClick={() => { setToken(''); setInventory(null); setPage('overview'); }}>
            <span className="avatar">{username.slice(0, 1).toUpperCase() || 'A'}</span><span className="user-copy"><strong>{username}</strong><small>Administrator</small></span><LogOut size={15} />
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumbs"><span>NetworkPath</span><ChevronRight size={14} /><strong>{pageTitle}</strong></div>
          <div className="topbar-actions"><span className="system-status"><i /> Control plane operational</span><button className="icon-button" aria-label="Refresh data" onClick={() => void refresh(token)} disabled={loading}><Activity size={17} /></button></div>
        </header>
        <div className="page-content">
          <div className="page-heading">
            <div><p className="eyebrow">NETWORK OPERATIONS</p><h1>{pageTitle}</h1><p className="muted">{page === 'overview' ? 'A live view of your distributed testing infrastructure.' : page === 'sites' ? 'Manage locations across your network.' : 'Monitor connected testing agents and their health.'}</p></div>
            {page === 'sites' && <button className="primary-button" onClick={() => document.getElementById('site-name')?.focus()}><Plus size={16} /> Add site</button>}
          </div>

          {error && <div className="banner-error" role="alert">{error}</div>}
          {loading && !inventory ? <div className="loading-state"><div className="spinner" /> Loading control-center data…</div> : null}
          {inventory && page === 'overview' && (
            <>
              <section className="stat-grid" aria-label="Network summary">
                <StatCard icon={<Building2 size={18} />} label="Total sites" value={overview?.total_sites ?? 0} caption="Configured locations" tone="blue" />
                <StatCard icon={<Server size={18} />} label="Registered agents" value={overview?.total_agents ?? 0} caption={`${onlineCount} currently online`} tone="violet" />
                <StatCard icon={<Wifi size={18} />} label="Online agents" value={onlineCount} caption={offlineCount ? `${offlineCount} offline` : 'All systems reachable'} tone="green" />
                <StatCard icon={<Gauge size={18} />} label="Active tests" value={overview?.active_tests ?? 0} caption="Currently executing" tone="amber" />
              </section>
              <section className="content-grid">
                <article className="panel health-panel">
                  <PanelHeading title="Agent availability" subtitle="Current connectivity across your fleet" icon={<Radio size={17} />} />
                  {agents.length ? <Suspense fallback={<div className="loading-state">Loading chart…</div>}><AgentAvailabilityChart onlineCount={onlineCount} offlineCount={offlineCount} totalCount={agents.length} /></Suspense> : <EmptyState icon={<Server size={22} />} title="No agents connected" description="Once agents register, their availability will appear here." />}
                </article>
                <article className="panel activity-panel">
                  <PanelHeading title="Recent activity" subtitle="Latest agent inventory" icon={<Activity size={17} />} />
                  {agents.length ? <div className="activity-list">{agents.slice(0, 5).map((agent) => <AgentRow key={agent.id} agent={agent} siteName={sites.find((site) => site.id === agent.site_id)?.name ?? 'Unassigned'} />)}</div> : <EmptyState icon={<Blocks size={22} />} title="Nothing to report yet" description="Agent status and test activity will show up here." />}
                </article>
              </section>
              <article className="panel trend-panel">
                <PanelHeading title="Network health" subtitle="Historical test measurements" icon={<Activity size={17} />} />
                <EmptyState icon={<Gauge size={22} />} title="No test results yet" description="Historical latency, packet loss, and throughput trends will appear after your first test." />
              </article>
            </>
          )}

          {inventory && page === 'sites' && (
            <section className="inventory-layout">
              <article className="panel table-panel">
                <PanelHeading title="Locations" subtitle={`${sites.length} configured ${sites.length === 1 ? 'site' : 'sites'}`} icon={<Building2 size={17} />} />
                {sites.length ? <div className="table-scroll"><table><thead><tr><th>SITE</th><th>REGION</th><th>CATEGORY</th><th>AGENTS</th></tr></thead><tbody>{sites.map((site) => <tr key={site.id}><td><strong>{site.name}</strong></td><td>{site.region || '—'}</td><td>{site.category || '—'}</td><td>{agents.filter((agent) => agent.site_id === site.id).length}</td></tr>)}</tbody></table></div> : <EmptyState icon={<Building2 size={22} />} title="No sites created" description="Create a site to organize your distributed agents." />}
              </article>
              <article className="panel create-panel">
                <PanelHeading title="Add a site" subtitle="Create a network location" icon={<Plus size={17} />} />
                <form className="site-form" onSubmit={(event) => void handleCreateSite(event)}><label htmlFor="site-name">Site name</label><input id="site-name" value={siteName} onChange={(event) => setSiteName(event.target.value)} placeholder="e.g. pi-dc-lab" maxLength={120} required /><label htmlFor="site-region">Region <span>Optional</span></label><input id="site-region" value={siteRegion} onChange={(event) => setSiteRegion(event.target.value)} placeholder="e.g. West" maxLength={120} /><button className="primary-button" type="submit"><Plus size={16} /> Create site</button></form>
              </article>
            </section>
          )}

          {inventory && page === 'agents' && (
            <article className="panel table-panel">
              <PanelHeading title="Agent inventory" subtitle={`${agents.length} registered ${agents.length === 1 ? 'agent' : 'agents'}`} icon={<Server size={17} />} />
              {agents.length ? <div className="table-scroll"><table><thead><tr><th>AGENT</th><th>SITE</th><th>STATUS</th><th>PLATFORM</th><th>LAST SEEN</th><th>ENGINES</th></tr></thead><tbody>{agents.map((agent) => <tr key={agent.id}><td><strong>{agent.name}</strong><small className="cell-subtitle">{agent.hostname ?? 'Hostname unavailable'}</small></td><td>{sites.find((site) => site.id === agent.site_id)?.name ?? 'Unassigned'}</td><td><StatusBadge status={agent.status} /></td><td>{[agent.os_name, agent.architecture].filter(Boolean).join(' · ') || '—'}</td><td>{agent.last_seen_at ? new Date(agent.last_seen_at).toLocaleString() : 'Never'}</td><td>{agent.available_engines.length ? agent.available_engines.join(', ') : '—'}</td></tr>)}</tbody></table></div> : <EmptyState icon={<Server size={22} />} title="No agents registered" description="Agent registration and authenticated connections are coming in the next development phase." />}
            </article>
          )}
        </div>
      </main>
    </div>
  );
}

function StatCard({ icon, label, value, caption, tone }: { icon: React.ReactNode; label: string; value: number; caption: string; tone: string }) {
  const iconForCaption = label === 'Online agents' ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />;
  return <article className="stat-card"><div className="stat-top"><div className={`stat-icon ${tone}`}>{icon}</div><span className="stat-label">{label}</span></div><div className="stat-value">{value}</div><div className="stat-caption">{label === 'Online agents' && value > 0 ? <span className="positive-caption">{iconForCaption}</span> : null}{caption}</div></article>;
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

export default App;
