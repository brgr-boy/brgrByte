import type { Agent, Overview, Site, TestSession, TokenResponse } from './types';

const apiBase = import.meta.env.VITE_API_BASE_URL ?? '';

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((item: { msg?: string }) => item.msg ?? 'Invalid input').join('; ') : `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const response = await fetch(`${apiBase}/api/v1/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Sign in failed (${response.status})`);
  }
  return response.json() as Promise<TokenResponse>;
}

export const getOverview = (token: string) => request<Overview>('/api/v1/overview', token);
export const getSites = (token: string) => request<Site[]>('/api/v1/sites', token);
export const getAgents = (token: string) => request<Agent[]>('/api/v1/agents', token);
export const getTests = (token: string) => request<TestSession[]>('/api/v1/tests', token);

export const createAgent = (token: string, name: string, site_id: string | null) =>
  request<{ id: string; credential: string }>('/api/v1/agents', token, {
    method: 'POST', body: JSON.stringify({ name, site_id }),
  });

export const revokeAgent = (token: string, id: string) =>
  request<void>(`/api/v1/agents/${id}/revoke`, token, { method: 'POST' });

export const createMtr = (token: string, source_agent_id: string, target: string, cycles: number) =>
  request<TestSession>('/api/v1/tests/mtr', token, {
    method: 'POST', body: JSON.stringify({ source_agent_id, target, cycles }),
  });

export const createIperf = (token: string, config: { source_agent_id: string; destination_agent_id: string | null; target: string; port: number; duration: number }) =>
  request<TestSession>('/api/v1/tests/iperf3', token, { method: 'POST', body: JSON.stringify(config) });

export const createSipp = (token: string, config: { source_agent_id: string; target: string; port: number; service: string; calls: number; rate: number; concurrency: number }) =>
  request<TestSession>('/api/v1/tests/sipp', token, { method: 'POST', body: JSON.stringify(config) });

export const createNmap = (token: string, source_agent_id: string, target: string, ports: number[]) =>
  request<TestSession>('/api/v1/tests/nmap', token, { method: 'POST', body: JSON.stringify({ source_agent_id, target, ports }) });

export const createPing = (token: string, source_agent_id: string, target: string, count: number) =>
  request<TestSession>('/api/v1/tests/ping', token, { method: 'POST', body: JSON.stringify({ source_agent_id, target, count }) });

export const createTraceroute = (token: string, source_agent_id: string, target: string) =>
  request<TestSession>('/api/v1/tests/traceroute', token, { method: 'POST', body: JSON.stringify({ source_agent_id, target }) });

export const createSite = (token: string, site: Pick<Site, 'name' | 'region' | 'category'>) =>
  request<Site>('/api/v1/sites', token, { method: 'POST', body: JSON.stringify(site) });
