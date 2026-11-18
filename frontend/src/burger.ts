export type Engine = 'mtr' | 'iperf3' | 'sipp' | 'nmap' | 'ping' | 'traceroute' | 'dns';

export const tools: { id: Engine; name: string; description: string }[] = [
  { id: 'mtr', name: 'MTR', description: 'Path, latency and loss' },
  { id: 'ping', name: 'Ping', description: 'ICMP reachability' },
  { id: 'traceroute', name: 'Traceroute', description: 'UDP path to a host' },
  { id: 'dns', name: 'DNS', description: 'Query a DNS server' },
  { id: 'nmap', name: 'Nmap', description: 'TCP port scan' },
  { id: 'iperf3', name: 'iPerf3', description: 'TCP throughput' },
  { id: 'sipp', name: 'SIPp', description: 'SIP call load' },
];

export type Combo = {
  name: string;
  description: string;
  engines: Engine[];
  settings: { cycles?: number; pingCount?: number; scanPorts?: string };
};

export const combos: Combo[] = [
  { name: 'Path combo', description: 'Ping + MTR + traceroute', engines: ['ping', 'mtr', 'traceroute'], settings: { pingCount: 4, cycles: 10 } },
  { name: 'Service combo', description: 'Ping + TCP ports', engines: ['ping', 'nmap'], settings: { pingCount: 4, scanPorts: '22,80,443' } },
];

export function eligibleSource(engines: Engine[], available: string[]): boolean {
  return engines.length > 0 && engines.every((engine) => available.includes(engine));
}

export async function placeOrder(
  engines: Engine[],
  submit: (engine: Engine) => Promise<unknown>,
): Promise<{ queued: Engine[]; failed: { engine: Engine; error: string }[] }> {
  const queued: Engine[] = [];
  const failed: { engine: Engine; error: string }[] = [];
  for (const engine of engines) {
    try {
      await submit(engine);
      queued.push(engine);
    } catch (error) {
      failed.push({ engine, error: error instanceof Error ? error.message : 'Request failed' });
    }
  }
  return { queued, failed };
}
