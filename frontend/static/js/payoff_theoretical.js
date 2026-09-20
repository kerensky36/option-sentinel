/**
 * payoff_theoretical.js — Black-Scholes theoretical pricing for the T+0 payoff overlay.
 *
 * Pure ES module: no DOM, no side effects. Imports only from payoff_math.js
 * (never modifies it — see specs/016-t0-payoff-overlay/plan.md Complexity Tracking).
 *
 * bsPrice mirrors src/services/bs_calculator.py::_bs_price exactly. Formulas
 * are verified against that production function in tests/unit/test_bs_pricing.py.
 */

import { combinedPayoff } from './payoff_math.js';

// Mirrors RISK_FREE_RATE in .env / src/services/greeks_service.py.
// Update both if the risk-free rate assumption ever changes (research.md D-003).
const RISK_FREE_RATE = 0.045;

/**
 * Fixed set of "view as of" checkpoints (research.md D-005).
 * offsetDays: null means "use the existing intrinsic-only formula" (Expiration).
 */
export const CHECKPOINTS = [
  { id: 'today',      label: 'Today',      offsetDays: 0 },
  { id: 'plus1wk',    label: '+1 week',    offsetDays: 7 },
  { id: 'plus2wk',    label: '+2 weeks',   offsetDays: 14 },
  { id: 'expiration', label: 'Expiration', offsetDays: null },
];

/**
 * Standard normal CDF via the Abramowitz & Stegun rational approximation
 * (accurate to ~1.5e-7) — JS has no built-in equivalent to scipy.stats.norm.cdf.
 * @param {number} x
 * @returns {number}
 */
function normCdf(x) {
  const sign = x < 0 ? -1 : 1;
  const ax = Math.abs(x) / Math.SQRT2;
  const a1 = 0.254829592, a2 = -0.284496736, a3 = 1.421413741,
        a4 = -1.453152027, a5 = 1.061405429, p = 0.3275911;
  const t = 1 / (1 + p * ax);
  const y = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-ax * ax);
  return 0.5 * (1 + sign * y);
}

/**
 * Black-Scholes theoretical price of one option.
 * Mirrors bs_calculator.py::_bs_price exactly.
 *
 * @param {number} S - Underlying price
 * @param {number} K - Strike price
 * @param {number} T - Time to expiry, in years
 * @param {number} r - Risk-free rate
 * @param {number} sigma - Implied volatility
 * @param {string} optionType - 'call' | 'put'
 * @returns {number}
 */
export function bsPrice(S, K, T, r, sigma, optionType) {
  const d1 = (Math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * Math.sqrt(T));
  const d2 = d1 - sigma * Math.sqrt(T);
  if (optionType === 'call') {
    return S * normCdf(d1) - K * Math.exp(-r * T) * normCdf(d2);
  }
  return K * Math.exp(-r * T) * normCdf(-d2) - S * normCdf(-d1);
}

/**
 * Filters CHECKPOINTS to those available for a position with the given
 * days to expiry (FR-004): a checkpoint is available if it has no fixed
 * offset (Expiration) or its offset is strictly less than daysToExpiry.
 * @param {number} daysToExpiry
 * @returns {Array}
 */
export function availableCheckpoints(daysToExpiry) {
  return CHECKPOINTS.filter((c) => c.offsetDays === null || c.offsetDays < daysToExpiry);
}

/**
 * Whether a position is eligible for the Today/checkpoint overlay at all
 * (FR-001, FR-008): every leg must have a usable implied volatility, and
 * there must be more than zero days to expiry (FR-001's own gate — also
 * covers the zero-DTE edge case per spec.md Edge Cases).
 * @param {Array} legs
 * @returns {boolean}
 */
export function isEligibleForOverlay(legs) {
  if (!legs || legs.length === 0) return false;
  const daysToExpiry = legs[0].daysToExpiry;
  if (!(daysToExpiry > 0)) return false;
  return legs.every((leg) => leg.impliedVolatility && leg.impliedVolatility > 0);
}

/**
 * P&L per share for one leg if valued today (or at any given daysToExpiry),
 * rather than at expiration. Parallel to legPayoffPerShare in payoff_math.js,
 * substituting bsPrice for intrinsic value.
 * @param {{strike:number, optionType:string, quantity:number, cost:number, impliedVolatility:number}} leg
 * @param {number} price
 * @param {number} daysToExpiry
 * @returns {number}
 */
export function theoreticalPayoffPerShare(leg, price, daysToExpiry) {
  const T = daysToExpiry / 365;
  const theoretical = bsPrice(price, leg.strike, T, RISK_FREE_RATE, leg.impliedVolatility, leg.optionType);
  const sign = leg.quantity > 0 ? 1 : -1;
  return sign * theoretical - leg.cost;
}

/**
 * Combined theoretical P&L per share across all legs at a given price/time.
 * @param {Array} legs
 * @param {number} price
 * @param {number} daysToExpiry
 * @returns {number}
 */
export function combinedTheoreticalPayoff(legs, price, daysToExpiry) {
  return legs.reduce((sum, leg) => sum + theoreticalPayoffPerShare(leg, price, daysToExpiry), 0);
}

/**
 * Evaluates one checkpoint across the same price grid analyzePayoff(legs).curve
 * already produces, so both curves share one x-axis (research.md D-006).
 * The "Expiration" checkpoint (offsetDays === null) routes through the
 * existing intrinsic-only combinedPayoff — this is what makes it coincide
 * exactly with the reference curve (FR-005), by construction.
 * @param {Array} legs
 * @param {{id:string, offsetDays:number|null}} checkpoint
 * @param {Array<{price:number, pnl:number}>} priceGrid
 * @returns {Array<{price:number, pnl:number}>}
 */
export function computeCheckpointCurve(legs, checkpoint, priceGrid) {
  if (checkpoint.offsetDays === null) {
    return priceGrid.map((pt) => ({ price: pt.price, pnl: combinedPayoff(legs, pt.price) }));
  }
  const daysToExpiry = legs[0].daysToExpiry - checkpoint.offsetDays;
  return priceGrid.map((pt) => ({ price: pt.price, pnl: combinedTheoreticalPayoff(legs, pt.price, daysToExpiry) }));
}
