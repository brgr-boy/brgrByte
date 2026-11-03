import type { Agent, Overview, Site, TokenResponse } from './types';

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
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
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

export const createSite = (token: string, site: Pick<Site, 'name' | 'region' | 'category'>) =>
  request<Site>('/api/v1/sites', token, { method: 'POST', body: JSON.stringify(site) });
