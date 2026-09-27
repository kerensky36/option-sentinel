// Node harness for tests/unit/test_quorum_ui.py (specs/020 T001).
// Usage: node quorum_ui_harness.mjs <calls.json>
// calls.json: { "calls": [ { "module": "quorum_ring"|"quorum_ui"|"positions_rows"|"demo_quorum",
//                            "fn": "<export>", "args": [...], "async": bool } ] }
// Prints { "results": [...], "storage_writes": [...], "fetches": [...] }.
import { readFileSync } from 'node:fs';

const storageWrites = [];
const fetches = [];
function storageSpy(name) {
  const data = {};
  return {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { storageWrites.push([name, k]); data[k] = String(v); },
    removeItem: (k) => { delete data[k]; },
    clear: () => {},
  };
}
globalThis.sessionStorage = storageSpy('sessionStorage');
globalThis.localStorage = storageSpy('localStorage');
globalThis.window ??= { location: { origin: 'http://localhost' } };

const MODULES = {
  quorum_ring: '../../frontend/static/js/quorum_ring.js',
  quorum_ui: '../../frontend/static/js/quorum_ui.js',
  positions_rows: '../../frontend/static/js/positions_rows.js',
  demo_quorum: '../../frontend/static/js/demo_quorum.js',
  demo_data: '../../frontend/static/js/demo_data.js',
};

// Special argument markers let Python describe JS-only values.
function reviveArg(a) {
  if (a && typeof a === 'object' && a.__fake_fetch__) {
    const spec = a.__fake_fetch__;
    return async (url, opts) => {
      fetches.push({ url, body: opts && opts.body ? JSON.parse(opts.body) : null });
      if (spec.throw) throw new Error('network');
      if (spec.hang) {
        return new Promise((_, reject) => {
          opts?.signal?.addEventListener('abort', () => reject(new Error('aborted')));
        });
      }
      return {
        ok: spec.status >= 200 && spec.status < 300,
        status: spec.status,
        json: async () => spec.body,
      };
    };
  }
  if (a && typeof a === 'object' && '__const__' in a) {
    const v = a.__const__;
    return () => v;
  }
  if (a && typeof a === 'object' && a.__event__) {
    const ev = a.__event__;
    const log = { stopped: false };
    return {
      __log: log,
      target: { closest: (sel) => (ev.matches || []).includes(sel) ? { getAttribute: () => ev.id, closest: () => ({}) } : null },
      stopPropagation: () => { log.stopped = true; },
    };
  }
  if (a && typeof a === 'object' && a.__fake_root__) {
    const log = [];
    return { __log: log, querySelectorAll: (sel) => { log.push(sel); return []; } };
  }
  return a;
}

const input = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const results = [];
for (const call of input.calls || []) {
  const mod = await import(MODULES[call.module]);
  const fn = mod[call.fn];
  if (typeof fn !== 'function') {
    results.push({ __value__: fn });
    continue;
  }
  const args = (call.args || []).map(reviveArg);
  let value = fn(...args);
  if (call.async || value instanceof Promise) value = await value;
  if (typeof Response !== 'undefined' && value instanceof Response) {
    value = { status: value.status, json: await value.json() };
  }
  const logs = args.filter((x) => x && x.__log).map((x) => x.__log);
  results.push(logs.length ? { value, logs } : value);
}
console.log(JSON.stringify({ results, storage_writes: storageWrites, fetches }));
