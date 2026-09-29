// Node harness for tests/unit/test_mode_switch.py (specs/021).
// Usage: node mode_switch_harness.mjs <steps.json>
// steps.json: { "storage": {k: v}, "steps": [ { "module", "fn", "args" } ] }
// Prints { "results": [...], "storage": {...}, "nav": [...] }.
import { readFileSync } from 'node:fs';

const input = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const data = { ...(input.storage || {}) };
globalThis.sessionStorage = {
  getItem: (k) => (k in data ? data[k] : null),
  setItem: (k, v) => { data[k] = String(v); },
  removeItem: (k) => { delete data[k]; },
  clear: () => { for (const k of Object.keys(data)) delete data[k]; },
};
const nav = [];
const fakeLocation = {
  pathname: '/screener',
  reload: () => nav.push(['reload']),
  assign: (u) => nav.push(['assign', u]),
  replace: (u) => nav.push(['replace', u]),
};
globalThis.window = { location: fakeLocation };

const MODULES = {
  auth: '../../frontend/static/js/auth.js',
  position_cache: '../../frontend/static/js/position_cache.js',
  screener_cache: '../../frontend/static/js/screener_cache.js',
  quorum_cache: '../../frontend/static/js/quorum_cache.js',
};

const results = [];
for (const step of input.steps) {
  if (step.set_demo !== undefined) {
    if (step.set_demo) data.demo_mode = 'true'; else delete data.demo_mode;
    results.push(null);
    continue;
  }
  const mod = await import(new URL(MODULES[step.module], import.meta.url));
  const args = (step.args || []).map((a) => (a === '__location__' ? fakeLocation : a));
  const out = await mod[step.fn](...args);
  results.push(out === undefined ? null : out);
}
console.log(JSON.stringify({ results, storage: data, nav }));
