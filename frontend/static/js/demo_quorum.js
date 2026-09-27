/**
 * demo_quorum.js — Tailored demo-mode quorum (specs/019).
 *
 * Pure ES module: no DOM, no network. Takes the same request body the live
 * quorum receives ({as_of, legs[]}) and returns a QuorumResult-shaped object
 * whose five votes come from fixed rules over the position's own figures, so
 * every rationale quotes real numbers from the clicked position. No model is
 * involved; the rules are illustrative only.
 *
 * Demo data conventions: cost is signed per share (negative = premium
 * received), quantity is signed (negative = short).
 */

import { analyzePayoff } from './payoff_math.js';

const RISK_FREE_RATE = 0.045;

/** Standard normal CDF (Abramowitz–Stegun 7.1.26, |error| < 1.5e-7). */
function normCdf(x) {
  const t = 1 / (1 + 0.3275911 * Math.abs(x) / Math.SQRT2);
  const poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))));
  const erf = 1 - poly * Math.exp(-(x * x) / 2);
  return x >= 0 ? (1 + erf) / 2 : (1 - erf) / 2;
}

/** Black-Scholes risk-neutral chance of finishing in the money: N(d2) call, N(−d2) put. */
function probItm(S, K, sigma, dte, optionType) {
  if (!S || !K || !sigma) return null;
  const T = Math.max(dte, 1) / 365;
  const d2 = (Math.log(S / K) + (RISK_FREE_RATE - 0.5 * sigma * sigma) * T) / (sigma * Math.sqrt(T));
  return optionType === 'call' ? normCdf(d2) : normCdf(-d2);
}

const DISCLAIMER = 'Informational only — not financial advice. Option Sentinel never places trades.';

const num = (v) => (v === null || v === undefined || v === '' ? null : Number(v));
const signed = (n) => `${n > 0 ? '+' : ''}${n}`;
const money = (n) => `$${Math.abs(Math.round(n)).toLocaleString('en-US')}`;

/** Figures the seat rules read (specs/019 plan.md). */
export function demoFigures(legs) {
  const parsed = legs.map((l) => ({
    ...l,
    strike: num(l.strike),
    cost: num(l.cost),
    delta: num(l.delta),
    theta: num(l.theta),
    iv: num(l.implied_volatility),
    rv: num(l.realised_volatility),
    price: num(l.underlying_price),
    pnl: num(l.unrealised_pnl) ?? 0,
  }));

  const sumOrNull = (fn) => (parsed.some((l) => fn(l) === null) ? null : parsed.reduce((s, l) => s + fn(l), 0));
  const netDelta = sumOrNull((l) => (l.delta === null ? null : l.delta * l.quantity * 100));
  const thetaDay = sumOrNull((l) => (l.theta === null ? null : l.theta * l.quantity * 100));

  const volIndex = parsed.findIndex((l) => l.iv && l.rv);
  const volLeg = volIndex >= 0 ? parsed[volIndex] : null;
  const ivRv = volLeg ? volLeg.iv / volLeg.rv : null;

  const dte = Math.min(...parsed.map((l) => l.days_to_expiry));
  const credit = -parsed.reduce((s, l) => s + (l.cost ?? 0) * Math.abs(l.quantity), 0);
  const pnl = parsed.reduce((s, l) => s + l.pnl, 0);
  const pctCaptured = credit > 0 ? (pnl / (credit * 100)) * 100 : null;

  const moneyness = (l) => {
    if (!l.price) return null;
    return ((l.option_type === 'call' ? l.price - l.strike : l.strike - l.price) / l.price) * 100;
  };
  const shorts = parsed.filter((l) => l.quantity < 0);
  const pool = shorts.length ? shorts : parsed;
  const keyLeg = pool.reduce((best, l) => {
    const m = moneyness(l);
    const b = moneyness(best);
    if (m === null) return best;
    return b === null || Math.abs(m) < Math.abs(b) ? l : best;
  }, pool[0]);

  let breakevens = [];
  if (parsed.every((l) => l.strike !== null && l.cost !== null)) {
    const payoffLegs = parsed.map((l) => ({
      strike: l.strike, optionType: l.option_type, quantity: l.quantity, cost: l.cost,
    }));
    breakevens = analyzePayoff(payoffLegs).breakevens;
  }

  return {
    legs: parsed,
    volIndex,
    keyIndex: parsed.indexOf(keyLeg),
    netDelta: netDelta === null ? null : Math.round(netDelta),
    thetaDay,
    ivRv,
    dte,
    credit,
    pnl,
    pctCaptured,
    keyLeg,
    keyIsShort: keyLeg.quantity < 0,
    moneyness: moneyness(keyLeg),
    probItm: probItm(keyLeg.price, keyLeg.strike, keyLeg.iv, keyLeg.days_to_expiry, keyLeg.option_type),
    breakevens,
  };
}

const vote = (seat, lens, action, confidence, rationale, roll_direction = null) => ({
  seat, lens, action, confidence, rationale, roll_direction: action === 'ROLL' ? roll_direction : null, abstained: false,
});

function greeksVote(f) {
  const lens = 'Greeks & Exposure';
  if (f.netDelta === null) {
    return vote('greeks_exposure', lens, 'HOLD', 0.3, 'Net delta is unavailable for this position, so exposure cannot be judged; holding.');
  }
  const delta = `Net delta is ${signed(f.netDelta)} shares`;
  if (f.keyIsShort && f.dte <= 7) {
    return vote('greeks_exposure', lens, 'ROLL', 0.7,
      `${delta} with only ${f.dte} days to expiry, so gamma risk on the short leg is climbing; rolling out resets it.`, 'out');
  }
  if (Math.abs(f.netDelta) >= 40) {
    return vote('greeks_exposure', lens, 'CLOSE', 0.6,
      `${delta} — a large directional bet for this size; closing removes the exposure.`);
  }
  return vote('greeks_exposure', lens, 'HOLD', 0.55,
    `${delta} with ${f.dte} days to expiry; exposure is modest, so holding is reasonable.`);
}

function volatilityVote(f) {
  const lens = 'Volatility & Pricing';
  if (f.ivRv === null) {
    return vote('volatility_pricing', lens, 'HOLD', 0.3,
      'Realised volatility is unavailable, so IV/RV cannot be judged; holding with low confidence.');
  }
  const ratio = `IV/RV is ${f.ivRv.toFixed(2)}×`;
  if (f.credit > 0) {
    if (f.ivRv >= 1.2) return vote('volatility_pricing', lens, 'HOLD', 0.6, `${ratio}: the premium sold is still rich, which favours staying short.`);
    if (f.ivRv <= 0.9) return vote('volatility_pricing', lens, 'CLOSE', 0.55, `${ratio}: the premium sold is now cheap relative to realised moves, so the edge is gone.`);
    return vote('volatility_pricing', lens, 'HOLD', 0.5, `${ratio}: implied volatility is roughly fair; no volatility reason to act.`);
  }
  if (f.ivRv >= 1.2) return vote('volatility_pricing', lens, 'CLOSE', 0.55, `${ratio}: the option you own is rich, so selling it back captures that premium.`);
  return vote('volatility_pricing', lens, 'HOLD', 0.5, `${ratio}: the option you own is not expensive; no volatility reason to sell.`);
}

function timeDecayVote(f) {
  const lens = 'Time Decay & P&L';
  if (f.credit > 0) {
    const pct = Math.round(f.pctCaptured);
    const captured = `${pct}% of max profit (${money(f.credit * 100)}) is captured with ${f.dte} days left`;
    if (f.pctCaptured >= 50) return vote('time_decay_pnl', lens, 'CLOSE', 0.7, `${captured}; taking the gain frees the risk for little remaining reward.`);
    if (f.pctCaptured >= 25 && f.dte <= 21) return vote('time_decay_pnl', lens, 'ROLL', 0.6, `${captured}; rolling out collects fresh premium before the final weeks.`, 'out');
    return vote('time_decay_pnl', lens, 'HOLD', 0.55, `${captured}; theta still has work to do.`);
  }
  const decay = f.thetaDay === null ? '' : ` Time decay costs about ${money(f.thetaDay)} a day.`;
  if (f.dte <= 14) return vote('time_decay_pnl', lens, 'CLOSE', 0.6, `A debit position with ${f.dte} days left loses value fastest from here.${decay}`);
  return vote('time_decay_pnl', lens, 'HOLD', 0.5, `A debit position with ${f.dte} days left still has time for the move it needs.${decay}`);
}

function strikeVote(f) {
  const lens = 'Strike & Assignment';
  if (f.moneyness === null) {
    return vote('strike_assignment', lens, 'HOLD', 0.3, 'The underlying price is unavailable, so strike distance cannot be judged; holding.');
  }
  const k = f.keyLeg;
  const where = f.moneyness >= 0
    ? `${Math.abs(f.moneyness).toFixed(1)}% in the money`
    : `${Math.abs(f.moneyness).toFixed(1)}% out of the money`;
  const prob = f.probItm === null ? '' : ` (≈${Math.round(f.probItm * 100)}% chance of finishing in the money)`;
  const leg = `The ${k.quantity < 0 ? 'short' : 'long'} ${Number(k.strike)} ${k.option_type} is ${where}${prob}`;
  if (f.keyIsShort && f.moneyness >= 0) {
    const dir = k.option_type === 'put' ? 'down_and_out' : 'up_and_out';
    return vote('strike_assignment', lens, 'ROLL', 0.7, `${leg}; assignment risk is real, so roll the strike away and out.`, dir);
  }
  if (f.keyIsShort && f.moneyness > -3 && f.dte <= 21) {
    return vote('strike_assignment', lens, 'ROLL', 0.6, `${leg} with ${f.dte} days left; rolling out adds cushion.`, 'out');
  }
  const be = f.breakevens.length ? ` Breakeven at expiry: $${f.breakevens.join(', $')}.` : '';
  return vote('strike_assignment', lens, 'HOLD', 0.55, `${leg}; there is room before assignment becomes a concern.${be}`);
}

function overlayVote(fundamentals, underlying) {
  const counts = {};
  for (const v of fundamentals) counts[v.action] = (counts[v.action] || 0) + 1;
  const ranked = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const action = ranked.length === 1 || ranked[0][1] > ranked[1][1] ? ranked[0][0] : 'HOLD';
  const dir = action === 'ROLL' ? (fundamentals.find((v) => v.action === 'ROLL')?.roll_direction || 'out') : null;
  return vote('macro_news_overlay', 'Macro & News Overlay', action, 0.5,
    `The demo news for ${underlying} is quiet, so it does not override the numbers; siding with the fundamentals analysts.`, dir);
}

function tally(votes) {
  const actions = ['CLOSE', 'HOLD', 'ROLL'];
  const rows = actions.map((action) => {
    const chosen = votes.filter((v) => v.action === action);
    const mean = chosen.length ? chosen.reduce((s, v) => s + v.confidence, 0) / chosen.length : null;
    return { action, votes: chosen.length, mean_confidence: mean === null ? null : Math.round(mean * 100) / 100 };
  });
  const winner = rows.find((t) => t.votes >= 3);
  return { rows, verdict: winner ? winner.action : 'NO_CONSENSUS' };
}

// ── specs/020: figure catalog, cited figures, demo summary token ─────────────

const _sign = (v) => (v < 0 ? '-' : '');
const FORMAT = {
  money: (v) => `${_sign(v)}$${Math.abs(v) >= 1000
    ? Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 })
    : Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
  pct: (v) => `${_sign(v)}${Math.abs(v) < 10 ? Math.abs(v).toFixed(1) : Math.abs(v).toFixed(0)}%`,
  ratio: (v) => `${v.toFixed(2)}×`,
  shares: (v) => `${v >= 0 ? '+' : '-'}${Math.abs(v).toFixed(0)} sh`,
  days: (v) => `${Math.trunc(v)} d`,
  count: (v) => String(Math.trunc(v)),
};

const SEAT_SHORT = {
  greeks_exposure: 'Greeks', volatility_pricing: 'Volatility', time_decay_pnl: 'Time decay',
  strike_assignment: 'Strike', macro_news_overlay: 'Macro',
};

/** Same names, labels and display formats as the server catalog (specs/020 D-304). */
export function demoCatalog(f, votes, tally) {
  const cat = {};
  const add = (name, label, value, kind, scale = 1) => {
    if (value === null || value === undefined || !Number.isFinite(Number(value) * scale)) return;
    cat[name] = { label, display: FORMAT[kind](Number(value) * scale) };
  };
  add('net_delta', 'Net delta', f.netDelta, 'shares');
  add('net_theta_day', 'Theta/day', f.thetaDay, 'money');
  if (f.credit > 0) {
    add('max_profit', 'Max profit', f.credit * 100, 'money');
    add('captured_pct', 'Captured', f.pctCaptured, 'pct');
  }
  f.breakevens.slice(0, 4).forEach((b, i) => add(`breakeven_${i + 1}`, i ? `Breakeven ${i + 1}` : 'Breakeven', b, 'money'));
  add('dte', 'DTE', f.dte, 'days');
  const single = f.legs.length === 1;
  f.legs.forEach((l, i) => {
    const n = i + 1;
    const label = (t) => (single ? t[0].toUpperCase() + t.slice(1) : `Leg ${n} ${t}`);
    add(`leg${n}_strike`, label('strike'), l.strike, 'money');
    add(`leg${n}_spot`, label('spot'), l.price, 'money');
    add(`leg${n}_iv`, label('IV'), l.iv, 'pct', 100);
    add(`leg${n}_rv`, label('RV'), l.rv, 'pct', 100);
    if (l.iv && l.rv) add(`leg${n}_iv_rv`, label('IV/RV'), l.iv / l.rv, 'ratio');
    if (l.price) {
      const m = ((l.option_type === 'call' ? l.price - l.strike : l.strike - l.price) / l.price) * 100;
      add(`leg${n}_moneyness`, label('moneyness'), m, 'pct');
    }
  });
  if (f.probItm !== null && f.keyIndex >= 0) add(`leg${f.keyIndex + 1}_prob_itm`, single ? 'P(ITM)' : `Leg ${f.keyIndex + 1} P(ITM)`, f.probItm, 'pct', 100);
  const counts = Object.fromEntries(tally.map((t) => [t.action, t.votes]));
  add('votes_close', 'Close votes', counts.CLOSE || 0, 'count');
  add('votes_hold', 'Hold votes', counts.HOLD || 0, 'count');
  add('votes_roll', 'Roll votes', counts.ROLL || 0, 'count');
  add('valid_votes', 'Valid votes', votes.length, 'count');
  add('seats', 'Seats', 5, 'count');
  for (const v of votes) add(`confidence_${v.seat}`, `${SEAT_SHORT[v.seat]} confidence`, v.confidence, 'pct', 100);
  return cat;
}

function demoCitedNames(seat, f) {
  const vol = f.volIndex >= 0 ? `leg${f.volIndex + 1}` : null;
  const key = f.keyIndex >= 0 ? `leg${f.keyIndex + 1}` : null;
  switch (seat) {
    case 'greeks_exposure': return ['net_delta', 'dte'];
    case 'volatility_pricing': return vol ? [`${vol}_iv_rv`, `${vol}_iv`, `${vol}_rv`] : [];
    case 'time_decay_pnl': return f.credit > 0 ? ['captured_pct', 'max_profit', 'dte'] : ['dte', 'net_theta_day'];
    case 'strike_assignment': return key ? [`${key}_moneyness`, `${key}_prob_itm`, 'breakeven_1'] : [];
    default: return [];
  }
}

function _b64url(text) {
  const bytes = new TextEncoder().encode(text);
  let bin = '';
  bytes.forEach((b) => { bin += String.fromCharCode(b); });
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function _unb64url(text) {
  const b64 = text.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (text.length % 4)) % 4);
  const bin = atob(b64);
  return new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)));
}

/** Decode a "demo." summary token; null for anything else. Never leaves the browser. */
export function decodeDemoToken(token) {
  if (typeof token !== 'string' || !token.startsWith('demo.')) return null;
  try {
    return JSON.parse(_unb64url(token.slice(5)));
  } catch {
    return null;
  }
}

const VERB = { CLOSE: 'close', HOLD: 'hold', ROLL: 'roll' };
const DIR = { out: ' out', up_and_out: ' up and out', down_and_out: ' down and out' };

/**
 * Template summary for demo mode (specs/020 FR-321, D-312). Uses the same
 * {name} placeholders as the live summariser and fills them from the catalog,
 * so every number shown comes from the demo figures.
 */
export function buildDemoSummary(payload) {
  const figs = payload.figures || {};
  const fill = (text) => text.replace(/\{([a-z0-9_]+)\}/g, (_, n) => (figs[n] ? figs[n].display : ''));
  const votes = (payload.votes || []).filter((v) => !v.abstained && v.action);
  const cites = (v) => {
    const names = (v.cited || []).filter((n) => figs[n]).slice(0, 2);
    return names.length ? ` It cited ${names.map((n) => `{${n}}`).join(' and ')}.` : '';
  };
  const verdict = payload.verdict;
  let title; let explanation; let why; let dissent;
  if (verdict === 'NO_CONSENSUS') {
    title = 'Demo: no majority, so the status quo is to hold.';
    explanation = 'No action reached a majority of the {seats} demo analysts. These demo votes come from fixed rules, not a model.';
    why = ['CLOSE', 'HOLD', 'ROLL']
      .filter((a) => votes.some((v) => v.action === a))
      .map((a) => `${a[0]}${a.slice(1).toLowerCase()}: {votes_${a.toLowerCase()}} of {seats} — ${votes.filter((v) => v.action === a).map((v) => v.lens).join(', ')}.`);
    dissent = 'With no majority there is no single dissent.';
  } else {
    const verb = VERB[verdict];
    title = `Demo: ${verb} the position${verdict === 'ROLL' && payload.roll_direction ? DIR[payload.roll_direction] : ''}.`;
    explanation = `{votes_${verb}} of {seats} demo analysts voted to ${verb}. These demo votes come from fixed rules, not a model.`;
    why = votes.filter((v) => v.action === verdict).slice(0, 4)
      .map((v) => `${v.lens}: ${verb} with {confidence_${v.seat}} confidence.${cites(v)}`);
    const others = votes.filter((v) => v.action !== verdict);
    dissent = others.length
      ? others.map((v) => `${v.lens} voted to ${VERB[v.action]}.`).join(' ')
      : 'No dissent: every voting demo analyst agreed.';
  }
  return {
    status: 'ok',
    trimmed: false,
    summary: { title: fill(title), explanation: fill(explanation), why: why.map(fill), dissent: fill(dissent) },
  };
}

/**
 * Build a demo QuorumResult for a v2 quorum request body (specs/019 FR-201–FR-206).
 * @param {{as_of: string, legs: Array<object>}} request
 */
export function buildDemoQuorum(request) {
  const legs = request?.legs?.length ? request.legs : [];
  const underlying = legs[0]?.underlying_symbol || 'DEMO';
  const hoursAgo = (h) => new Date(Date.now() - h * 3600 * 1000).toISOString();

  let votes = [];
  let breakevens = [];
  let f = null;
  if (legs.length) {
    f = demoFigures(legs);
    breakevens = f.breakevens;
    const fundamentals = [greeksVote(f), volatilityVote(f), timeDecayVote(f), strikeVote(f)];
    votes = [...fundamentals, overlayVote(fundamentals, underlying)];
  }
  const { rows, verdict } = tally(votes);

  // specs/020: cited figures and a demo summary token, all built in the browser.
  let summaryToken = null;
  if (f) {
    const catalog = demoCatalog(f, votes, rows);
    for (const v of votes) {
      v.cited_figures = demoCitedNames(v.seat, f)
        .filter((n) => catalog[n])
        .slice(0, 5)
        .map((n) => ({ name: n, label: catalog[n].label, display: catalog[n].display }));
    }
    if (votes.length) {
      const rollDirs = new Set(votes.filter((v) => v.action === 'ROLL').map((v) => v.roll_direction));
      const payload = {
        v: 1,
        underlying_symbol: underlying,
        verdict,
        roll_direction: rollDirs.size === 1 ? [...rollDirs][0] : null,
        tally: rows,
        votes: votes.map((v) => ({
          seat: v.seat, lens: v.lens, action: v.action, confidence: v.confidence,
          roll_direction: v.roll_direction, rationale: v.rationale,
          cited: v.cited_figures.map((c) => c.name), abstained: false,
        })),
        figures: catalog,
      };
      summaryToken = `demo.${_b64url(JSON.stringify(payload))}`;
    }
  }

  return {
    verdict: votes.length ? verdict : 'NO_QUORUM',
    quorum_met: votes.length === 5,
    seats: 5,
    valid_votes: votes.length,
    tally: rows,
    votes,
    macro_brief: `Demo: no live research in demo mode. A real quorum would summarise news and scheduled events for ${underlying} before expiry.`,
    headlines: [
      { publisher: 'Yahoo Finance', title: `Demo headline: What to watch for ${underlying} this week`, link: 'https://finance.yahoo.com/', published: hoursAgo(3), summary: '' },
      { publisher: 'CNBC', title: 'Demo headline: Fed holds rates steady, signals patience', link: 'https://www.cnbc.com/', published: hoursAgo(9), summary: '' },
      { publisher: 'Bloomberg', title: 'Demo headline: Treasury yields drift lower after inflation data', link: 'https://www.bloomberg.com/markets', published: hoursAgo(20), summary: '' },
    ],
    underlying_symbol: underlying,
    model: 'demo (no model call)',
    generated_at: new Date().toISOString(),
    as_of: request?.as_of || new Date().toISOString(),
    position_fundamentals: { breakevens },
    disclaimer: DISCLAIMER,
    summary_token: summaryToken,
  };
}
