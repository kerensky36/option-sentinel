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

  const volLeg = parsed.find((l) => l.iv && l.rv);
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
  if (legs.length) {
    const f = demoFigures(legs);
    breakevens = f.breakevens;
    const fundamentals = [greeksVote(f), volatilityVote(f), timeDecayVote(f), strikeVote(f)];
    votes = [...fundamentals, overlayVote(fundamentals, underlying)];
  }
  const { rows, verdict } = tally(votes);

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
  };
}
