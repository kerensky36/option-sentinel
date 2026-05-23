/**
 * payoff_math.js — Option payoff computation at expiration.
 *
 * Pure ES module: no imports, no DOM, no side effects.
 * Formula mirrors tests/unit/test_payoff_math.py exactly.
 *
 * Leg shape: { strike: number, optionType: 'call'|'put', quantity: number, cost: number }
 *   cost is signed: negative = received premium (short), positive = paid premium (long)
 *   quantity is signed: negative = short, positive = long
 */

/**
 * P&L per share for one option leg at expiration.
 * Formula: sign(quantity) * intrinsic - cost
 *
 * @param {{ strike: number, optionType: string, quantity: number, cost: number }} leg
 * @param {number} price - Underlying price at expiration
 * @returns {number}
 */
export function legPayoffPerShare(leg, price) {
  const intrinsic = leg.optionType === 'call'
    ? Math.max(price - leg.strike, 0)
    : Math.max(leg.strike - price, 0);
  const sign = leg.quantity > 0 ? 1 : -1;
  return sign * intrinsic - leg.cost;
}

/**
 * Combined net P&L per share across all legs at a given underlying price.
 *
 * @param {Array<{strike: number, optionType: string, quantity: number, cost: number}>} legs
 * @param {number} price
 * @returns {number}
 */
export function combinedPayoff(legs, price) {
  return legs.reduce((sum, leg) => sum + legPayoffPerShare(leg, price), 0);
}

/**
 * Analyse a set of legs and return their payoff profile.
 *
 * @param {Array<{strike: number, optionType: string, quantity: number, cost: number}>} legs
 * @returns {{
 *   maxGain: number,
 *   maxLoss: number,
 *   breakevens: number[],
 *   strikePrices: number[],
 *   curve: Array<{price: number, pnl: number}>
 * }}
 */
export function analyzePayoff(legs) {
  const strikes = [...new Set(legs.map(l => l.strike))].sort((a, b) => a - b);
  const priceMin = Math.min(...strikes) * 0.65;
  const priceMax = Math.max(...strikes) * 1.35;
  const step = (priceMax - priceMin) / 199;

  const curve = [];
  for (let i = 0; i < 200; i++) {
    const price = priceMin + i * step;
    curve.push({ price, pnl: combinedPayoff(legs, price) });
  }

  const pnls = curve.map(pt => pt.pnl);
  const maxGain = Math.max(...pnls);
  const maxLoss = Math.min(...pnls);

  const breakevens = [];
  for (let i = 0; i < curve.length - 1; i++) {
    const a = curve[i].pnl;
    const b = curve[i + 1].pnl;
    if ((a < 0 && b > 0) || (a > 0 && b < 0) || a === 0) {
      breakevens.push(Math.round(((curve[i].price + curve[i + 1].price) / 2) * 100) / 100);
    }
  }

  return { maxGain, maxLoss, breakevens, strikePrices: strikes, curve };
}
