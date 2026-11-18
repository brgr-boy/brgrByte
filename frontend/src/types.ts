export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
}

export interface Overview {
  total_sites: number;
  total_agents: number;
  online_agents: number;
  active_tests: number;
}

export interface Site {
  id: string;
  name: string;
  region: string | null;
  category: string | null;
  created_at: string;
}

export interface Agent {
  id: string;
  name: string;
  site_id: string | null;
  status: 'offline' | 'online' | 'degraded';
  hostname: string | null;
  os_name: string | null;
  architecture: string | null;
  version: string | null;
  last_seen_at: string | null;
  cpu_percent: number | null;
  memory_percent: number | null;
  available_engines: string[];
}

export interface TestSession {
  id: string;
  source_agent_id: string | null;
  destination_agent_id: string | null;
  engine: string;
  status: string;
  configuration: { target?: string; cycles?: number };
  created_at: string;
  completed_at: string | null;
  results: { agent_id: string | null; success: boolean; error: string | null; metrics: Record<string, unknown>; created_at: string }[];
}
