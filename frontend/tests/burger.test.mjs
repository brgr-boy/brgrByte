import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/burger.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { combos, eligibleSource, placeOrder, tools } = await import(`data:text/javascript,${encodeURIComponent(js)}`);

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
