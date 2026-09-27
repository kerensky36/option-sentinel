// Node harness for tests/unit/test_demo_quorum.py (specs/019 T001).
// Usage: node demo_quorum_harness.mjs <cases.json>
// cases.json: { "cases": { name: request }, "demo_spreads": bool, "realised_vol": {sym: rv} }
import { readFileSync } from 'node:fs';
import { buildDemoQuorum } from '../../frontend/static/js/demo_quorum.js';

const input = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const out = { cases: {}, demo_tallies: [], demo_verdicts: {} };

for (const [name, request] of Object.entries(input.cases || {})) {
  out.cases[name] = buildDemoQuorum(request);
}

if (input.demo_spreads) {
  const { DEMO_POSITIONS_SPREADS, DEMO_POSITIONS_EQUITY } = await import('../../frontend/static/js/demo_data.js');
  const LEG_FIELDS = [
    'underlying_symbol', 'option_type', 'strike', 'expiry_date', 'days_to_expiry',
    'quantity', 'cost', 'current_mark', 'unrealised_pnl', 'delta', 'gamma', 'theta',
    'vega', 'implied_volatility', 'underlying_price',
  ];
  const groups = {};
  for (const p of [...DEMO_POSITIONS_SPREADS, ...DEMO_POSITIONS_EQUITY]) {
    (groups[`${p.underlying_symbol}|${p.expiry_date}`] ||= []).push(p);
  }
  for (const legs of Object.values(groups)) {
    const request = {
      as_of: '2026-09-27T14:00:00Z',
      legs: legs.map((l) => {
        const o = {};
        for (const k of LEG_FIELDS) o[k] = l[k] ?? null;
        o.realised_volatility = input.realised_vol?.[l.underlying_symbol] ?? null;
        return o;
      }),
    };
    const r = buildDemoQuorum(request);
    out.demo_tallies.push(r.tally.map((t) => `${t.action}:${t.votes}`).join(','));
    out.demo_verdicts[`${legs[0].underlying_symbol} x${legs.length}`] = r.verdict;
  }
}

console.log(JSON.stringify(out));
