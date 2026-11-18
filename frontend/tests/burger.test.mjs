import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/burger.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { combos, eligibleSource, isPlainSeasoning, plainSeasoning, placeOrder, tools } = await import(`data:text/javascript,${encodeURIComponent(js)}`);

test('combos name real tools and require every tool on the source', () => {
  const known = new Set(tools.map((tool) => tool.id));
  assert.deepEqual(combos.map((combo) => combo.engines), [
    ['ping', 'mtr', 'traceroute'],
    ['ping', 'nmap'],
  ]);
  assert.deepEqual(combos.map((combo) => combo.settings), [
    { pingCount: 4, cycles: 10 },
    { pingCount: 4, scanPorts: '22,80,443' },
  ]);
  for (const combo of combos) {
    assert.ok(combo.engines.every((engine) => known.has(engine)));
    assert.ok(eligibleSource(combo.engines, combo.engines));
    assert.equal(eligibleSource(combo.engines, combo.engines.slice(1)), false);
  }
  assert.equal(eligibleSource([], ['ping']), false);
  assert.ok(known.has('dns'));
  assert.ok(eligibleSource(['ping', 'dns'], ['ping', 'dns']));
  assert.equal(eligibleSource(['ping', 'dns'], ['ping']), false);
});

test('orders queue one request per tool and retain partial failures', async () => {
  const calls = [];
  const result = await placeOrder(['ping', 'mtr', 'traceroute'], async (engine) => {
    calls.push(engine);
    if (engine === 'mtr') throw new Error('agent offline');
  });
  assert.deepEqual(calls, ['ping', 'mtr', 'traceroute']);
  assert.deepEqual(result, {
    queued: ['ping', 'traceroute'],
    failed: [{ engine: 'mtr', error: 'agent offline' }],
  });
});

test('seasonings are plain at tool defaults and become seasoned when a setting changes', () => {
  for (const tool of tools) {
    assert.equal(isPlainSeasoning(tool.id, plainSeasoning), true, `${tool.name} defaults to plain`);
  }
  assert.equal(isPlainSeasoning('mtr', { ...plainSeasoning, cycles: 12 }), false);
  assert.equal(isPlainSeasoning('ping', { ...plainSeasoning, pingCount: 6 }), false);
  assert.equal(isPlainSeasoning('traceroute', { ...plainSeasoning, maxHops: 12 }), false);
  assert.equal(isPlainSeasoning('dns', { ...plainSeasoning, dnsType: 'AAAA' }), false);
  assert.equal(isPlainSeasoning('nmap', { ...plainSeasoning, scanPorts: '443' }), false);
  assert.equal(isPlainSeasoning('iperf3', { ...plainSeasoning, duration: 30 }), false);
  assert.equal(isPlainSeasoning('iperf3', { ...plainSeasoning, destinationAgent: 'receiver-id' }), false);
  assert.equal(isPlainSeasoning('sipp', { ...plainSeasoning, calls: 100 }), false);
  assert.equal(isPlainSeasoning('sipp', { ...plainSeasoning, rate: 3 }), false);
  assert.equal(isPlainSeasoning('sipp', { ...plainSeasoning, concurrency: 20 }), false);
});
