/**
 * demo_data.js — Static fixture data for demo mode (feature 014).
 *
 * Loaded lazily by fetchWithAuth() in auth.js when isDemoMode() returns true.
 * All data shapes match the Pydantic model_dump(mode='json') output from the
 * corresponding server-side models (PositionView, ScreenerResultView).
 *
 * Two demo accounts:
 *   DEMO_SPREADS_HASH — option spread positions only
 *   DEMO_EQUITY_HASH  — covered calls + screener candidates (equities & ETFs)
 */

export const DEMO_SPREADS_HASH = 'demo-spreads-0001';
export const DEMO_EQUITY_HASH  = 'demo-equity-0002';

export const DEMO_ACCOUNTS = [
  { hashValue: DEMO_SPREADS_HASH, accountNumber: 'DEMO — Options Spreads' },
  { hashValue: DEMO_EQUITY_HASH,  accountNumber: 'DEMO — Equities & ETFs' },
];

export const DEMO_POSITIONS_SPREADS = [
  {
    symbol: 'AAPL 250718P00195000', underlying_symbol: 'AAPL', option_type: 'put',
    strike: '195.00', expiry_date: '2025-07-18', quantity: -1,
    cost: '-3.85', current_mark: '-2.40', unrealised_pnl: '145.00', days_to_expiry: 57,
    delta: -0.24, gamma: 0.041, theta: -0.09, vega: 0.17, implied_volatility: 0.30,
    delta_source: 'calculated', gamma_source: 'calculated',
    theta_source: 'calculated', vega_source: 'calculated', iv_source: 'calculated',
  },
  {
    symbol: 'AAPL 250718P00185000', underlying_symbol: 'AAPL', option_type: 'put',
    strike: '185.00', expiry_date: '2025-07-18', quantity: 1,
    cost: '1.95', current_mark: '1.10', unrealised_pnl: '-85.00', days_to_expiry: 57,
    delta: 0.13, gamma: 0.028, theta: 0.05, vega: 0.10, implied_volatility: 0.29,
    delta_source: 'calculated', gamma_source: 'calculated',
    theta_source: 'calculated', vega_source: 'calculated', iv_source: 'calculated',
  },
  {
    symbol: 'SPY 250620P00520000', underlying_symbol: 'SPY', option_type: 'put',
    strike: '520.00', expiry_date: '2025-06-20', quantity: -1,
    cost: '-4.20', current_mark: '-2.80', unrealised_pnl: '140.00', days_to_expiry: 29,
    delta: -0.25, gamma: 0.038, theta: -0.12, vega: 0.18, implied_volatility: 0.20,
    delta_source: 'calculated', gamma_source: 'calculated',
    theta_source: 'calculated', vega_source: 'calculated', iv_source: 'calculated',
  },
  {
    symbol: 'SPY 250620C00560000', underlying_symbol: 'SPY', option_type: 'call',
    strike: '560.00', expiry_date: '2025-06-20', quantity: -1,
    cost: '-2.10', current_mark: '-1.30', unrealised_pnl: '80.00', days_to_expiry: 29,
    delta: 0.22, gamma: 0.034, theta: -0.10, vega: 0.16, implied_volatility: 0.19,
    delta_source: 'calculated', gamma_source: 'calculated',
    theta_source: 'calculated', vega_source: 'calculated', iv_source: 'calculated',
  },
  {
    symbol: 'TSLA 250718C00280000', underlying_symbol: 'TSLA', option_type: 'call',
    strike: '280.00', expiry_date: '2025-07-18', quantity: -1,
    cost: '-6.50', current_mark: '-4.10', unrealised_pnl: '240.00', days_to_expiry: 57,
    delta: 0.31, gamma: 0.052, theta: -0.15, vega: 0.28, implied_volatility: 0.48,
    delta_source: 'calculated', gamma_source: 'calculated',
    theta_source: 'calculated', vega_source: 'calculated', iv_source: 'calculated',
  },
  {
    symbol: 'TSLA 250718C00295000', underlying_symbol: 'TSLA', option_type: 'call',
    strike: '295.00', expiry_date: '2025-07-18', quantity: 1,
    cost: '3.80', current_mark: '2.25', unrealised_pnl: '-155.00', days_to_expiry: 57,
    delta: -0.19, gamma: 0.038, theta: 0.09, vega: 0.21, implied_volatility: 0.47,
    delta_source: 'calculated', gamma_source: 'calculated',
    theta_source: 'calculated', vega_source: 'calculated', iv_source: 'calculated',
  },
];

export const DEMO_POSITIONS_EQUITY = [
  {
    symbol: 'AAPL 250620C00220000', underlying_symbol: 'AAPL', option_type: 'call',
    strike: '220.00', expiry_date: '2025-06-20', quantity: -1,
    cost: '-3.20', current_mark: '-2.05', unrealised_pnl: '115.00', days_to_expiry: 29,
    delta: 0.28, gamma: 0.040, theta: -0.11, vega: 0.14, implied_volatility: 0.29,
    delta_source: 'calculated', gamma_source: 'calculated',
    theta_source: 'calculated', vega_source: 'calculated', iv_source: 'calculated',
  },
  {
    symbol: 'NVDA 250620C00135000', underlying_symbol: 'NVDA', option_type: 'call',
    strike: '135.00', expiry_date: '2025-06-20', quantity: -1,
    cost: '-2.45', current_mark: '-1.60', unrealised_pnl: '85.00', days_to_expiry: 29,
    delta: 0.30, gamma: 0.058, theta: -0.14, vega: 0.19, implied_volatility: 0.42,
    delta_source: 'calculated', gamma_source: 'calculated',
    theta_source: 'calculated', vega_source: 'calculated', iv_source: 'calculated',
  },
  {
    symbol: 'VOO 250620C00510000', underlying_symbol: 'VOO', option_type: 'call',
    strike: '510.00', expiry_date: '2025-06-20', quantity: -1,
    cost: '-2.90', current_mark: '-1.70', unrealised_pnl: '120.00', days_to_expiry: 29,
    delta: 0.25, gamma: 0.032, theta: -0.08, vega: 0.12, implied_volatility: 0.16,
    delta_source: 'calculated', gamma_source: 'calculated',
    theta_source: 'calculated', vega_source: 'calculated', iv_source: 'calculated',
  },
  {
    symbol: 'SPY 250620C00570000', underlying_symbol: 'SPY', option_type: 'call',
    strike: '570.00', expiry_date: '2025-06-20', quantity: -2,
    cost: '-3.50', current_mark: '-2.20', unrealised_pnl: '260.00', days_to_expiry: 29,
    delta: 0.27, gamma: 0.035, theta: -0.10, vega: 0.16, implied_volatility: 0.18,
    delta_source: 'calculated', gamma_source: 'calculated',
    theta_source: 'calculated', vega_source: 'calculated', iv_source: 'calculated',
  },
  {
    symbol: 'AMD 250620C00175000', underlying_symbol: 'AMD', option_type: 'call',
    strike: '175.00', expiry_date: '2025-06-20', quantity: -2,
    cost: '-4.80', current_mark: '-3.10', unrealised_pnl: '340.00', days_to_expiry: 29,
    delta: 0.32, gamma: 0.062, theta: -0.16, vega: 0.22, implied_volatility: 0.51,
    delta_source: 'calculated', gamma_source: 'calculated',
    theta_source: 'calculated', vega_source: 'calculated', iv_source: 'calculated',
  },
  {
    symbol: 'META 250620C00620000', underlying_symbol: 'META', option_type: 'call',
    strike: '620.00', expiry_date: '2025-06-20', quantity: -1,
    cost: '-8.20', current_mark: '-5.40', unrealised_pnl: '280.00', days_to_expiry: 29,
    delta: 0.29, gamma: 0.028, theta: -0.13, vega: 0.24, implied_volatility: 0.34,
    delta_source: 'calculated', gamma_source: 'calculated',
    theta_source: 'calculated', vega_source: 'calculated', iv_source: 'calculated',
  },
];

// Candidate option contracts for demo screener results.
// Three DTE buckets cover all risk profiles:
//   21d → aggressive (7–30), 35d → balanced (30–45), 56d → conservative (30–60)
const _AAPL_CANDIDATES = [
  { dte: 21, delta: 0.31, bid: 2.60, strike: 220.0, expiry: '2026-06-12', open_interest: 2400 },
  { dte: 21, delta: 0.20, bid: 1.90, strike: 225.0, expiry: '2026-06-12', open_interest: 1800 },
  { dte: 35, delta: 0.27, bid: 3.30, strike: 220.0, expiry: '2026-06-26', open_interest: 1900 },
  { dte: 35, delta: 0.18, bid: 2.50, strike: 225.0, expiry: '2026-06-26', open_interest: 1400 },
  { dte: 56, delta: 0.24, bid: 3.90, strike: 220.0, expiry: '2026-07-17', open_interest: 1200 },
  { dte: 56, delta: 0.15, bid: 2.80, strike: 225.0, expiry: '2026-07-17', open_interest: 900 },
];
const _AMD_CANDIDATES = [
  { dte: 21, delta: 0.34, bid: 3.40, strike: 163.0, expiry: '2026-06-12', open_interest: 3100 },
  { dte: 21, delta: 0.22, bid: 2.20, strike: 168.0, expiry: '2026-06-12', open_interest: 2200 },
  { dte: 35, delta: 0.28, bid: 4.90, strike: 163.0, expiry: '2026-06-26', open_interest: 2000 },
  { dte: 35, delta: 0.17, bid: 3.30, strike: 168.0, expiry: '2026-06-26', open_interest: 1500 },
  { dte: 56, delta: 0.25, bid: 5.80, strike: 163.0, expiry: '2026-07-17', open_interest: 1400 },
  { dte: 56, delta: 0.14, bid: 3.80, strike: 170.0, expiry: '2026-07-17', open_interest: 900 },
];
const _NVDA_CANDIDATES = [
  { dte: 21, delta: 0.33, bid: 2.20, strike: 132.0, expiry: '2026-06-12', open_interest: 4200 },
  { dte: 21, delta: 0.21, bid: 1.60, strike: 135.0, expiry: '2026-06-12', open_interest: 3100 },
  { dte: 35, delta: 0.27, bid: 2.50, strike: 132.0, expiry: '2026-06-26', open_interest: 3000 },
  { dte: 35, delta: 0.17, bid: 1.80, strike: 135.0, expiry: '2026-06-26', open_interest: 2100 },
  { dte: 56, delta: 0.23, bid: 2.90, strike: 132.0, expiry: '2026-07-17', open_interest: 2000 },
  { dte: 56, delta: 0.14, bid: 2.00, strike: 137.0, expiry: '2026-07-17', open_interest: 1200 },
];
const _META_CANDIDATES = [
  { dte: 21, delta: 0.32, bid: 7.80, strike: 610.0, expiry: '2026-06-12', open_interest: 1100 },
  { dte: 21, delta: 0.22, bid: 5.60, strike: 620.0, expiry: '2026-06-12', open_interest: 800 },
  { dte: 35, delta: 0.26, bid: 8.40, strike: 610.0, expiry: '2026-06-26', open_interest: 900 },
  { dte: 35, delta: 0.17, bid: 6.20, strike: 625.0, expiry: '2026-06-26', open_interest: 650 },
  { dte: 56, delta: 0.22, bid: 9.60, strike: 615.0, expiry: '2026-07-17', open_interest: 700 },
  { dte: 56, delta: 0.14, bid: 7.10, strike: 630.0, expiry: '2026-07-17', open_interest: 500 },
];
const _SPY_CANDIDATES = [
  { dte: 21, delta: 0.30, bid: 2.90, strike: 568.0, expiry: '2026-06-12', open_interest: 9200 },
  { dte: 21, delta: 0.20, bid: 1.90, strike: 574.0, expiry: '2026-06-12', open_interest: 7100 },
  { dte: 35, delta: 0.25, bid: 3.60, strike: 568.0, expiry: '2026-06-26', open_interest: 6500 },
  { dte: 35, delta: 0.16, bid: 2.50, strike: 574.0, expiry: '2026-06-26', open_interest: 5000 },
  { dte: 56, delta: 0.22, bid: 4.20, strike: 568.0, expiry: '2026-07-17', open_interest: 4500 },
  { dte: 56, delta: 0.14, bid: 3.00, strike: 576.0, expiry: '2026-07-17', open_interest: 3200 },
];
const _VOO_CANDIDATES = [
  { dte: 21, delta: 0.28, bid: 2.30, strike: 514.0, expiry: '2026-06-12', open_interest: 900 },
  { dte: 21, delta: 0.18, bid: 1.60, strike: 520.0, expiry: '2026-06-12', open_interest: 680 },
  { dte: 35, delta: 0.23, bid: 3.00, strike: 514.0, expiry: '2026-06-26', open_interest: 720 },
  { dte: 35, delta: 0.15, bid: 2.10, strike: 520.0, expiry: '2026-06-26', open_interest: 540 },
  { dte: 56, delta: 0.20, bid: 3.50, strike: 514.0, expiry: '2026-07-17', open_interest: 480 },
  { dte: 56, delta: 0.13, bid: 2.40, strike: 522.0, expiry: '2026-07-17', open_interest: 350 },
];

export const DEMO_SCREENER_RESULTS = [
  {
    ticker: 'AAPL', shares: 150, contracts: 1, stock_price: 213.50,
    iv_rank: 42.0, recommended_strike: 220.00, recommended_expiry: '2026-06-26',
    bid_premium: 3.30, annualised_yield: 0.18, call_delta: 0.27,
    days_to_earnings: 45, composite_score: 78.5,
    recommendation_status: 'recommended', sort_order: 1, candidates: _AAPL_CANDIDATES,
  },
  {
    ticker: 'AMD', shares: 300, contracts: 2, stock_price: 158.40,
    iv_rank: 61.0, recommended_strike: 163.00, recommended_expiry: '2026-06-26',
    bid_premium: 4.90, annualised_yield: 0.34, call_delta: 0.28,
    days_to_earnings: 38, composite_score: 76.2,
    recommendation_status: 'recommended', sort_order: 2, candidates: _AMD_CANDIDATES,
  },
  {
    ticker: 'NVDA', shares: 200, contracts: 1, stock_price: 127.60,
    iv_rank: 58.0, recommended_strike: 132.00, recommended_expiry: '2026-06-26',
    bid_premium: 2.50, annualised_yield: 0.21, call_delta: 0.27,
    days_to_earnings: 52, composite_score: 74.8,
    recommendation_status: 'recommended', sort_order: 3, candidates: _NVDA_CANDIDATES,
  },
  {
    ticker: 'META', shares: 175, contracts: 1, stock_price: 592.30,
    iv_rank: 46.0, recommended_strike: 610.00, recommended_expiry: '2026-06-26',
    bid_premium: 8.40, annualised_yield: 0.17, call_delta: 0.26,
    days_to_earnings: 41, composite_score: 71.3,
    recommendation_status: 'recommended', sort_order: 4, candidates: _META_CANDIDATES,
  },
  {
    ticker: 'SPY', shares: 250, contracts: 2, stock_price: 558.70,
    iv_rank: 31.0, recommended_strike: 568.00, recommended_expiry: '2026-06-26',
    bid_premium: 3.60, annualised_yield: 0.14, call_delta: 0.25,
    days_to_earnings: null, composite_score: 64.1,
    recommendation_status: 'recommended', sort_order: 5, candidates: _SPY_CANDIDATES,
  },
  {
    ticker: 'VOO', shares: 150, contracts: 1, stock_price: 504.80,
    iv_rank: 28.0, recommended_strike: 514.00, recommended_expiry: '2026-06-26',
    bid_premium: 3.00, annualised_yield: 0.13, call_delta: 0.23,
    days_to_earnings: null, composite_score: 61.0,
    recommendation_status: 'recommended', sort_order: 6, candidates: _VOO_CANDIDATES,
  },
  {
    ticker: 'AMZN', shares: 120, contracts: 0, stock_price: 218.90,
    iv_rank: 39.0, recommended_strike: 225.00, recommended_expiry: '2026-06-26',
    bid_premium: 3.10, annualised_yield: 0.17, call_delta: 0.30,
    days_to_earnings: 8, composite_score: 52.4,
    recommendation_status: 'suppressed', sort_order: 7, candidates: [],
  },
  {
    ticker: 'MSFT', shares: 125, contracts: 0, stock_price: 421.10,
    iv_rank: 55.0, recommended_strike: 430.00, recommended_expiry: '2026-06-26',
    bid_premium: 4.10, annualised_yield: 0.12, call_delta: 0.31,
    days_to_earnings: 12, composite_score: 49.8,
    recommendation_status: 'suppressed', sort_order: 8, candidates: [],
  },
  {
    ticker: 'QQQ', shares: 200, contracts: 0, stock_price: 448.20,
    iv_rank: 18.0, recommended_strike: null, recommended_expiry: null,
    bid_premium: null, annualised_yield: null, call_delta: null,
    days_to_earnings: null, composite_score: 34.0,
    recommendation_status: 'suppressed', sort_order: 9, candidates: [],
  },
  {
    ticker: 'GOOGL', shares: 110, contracts: 0, stock_price: 174.50,
    iv_rank: 22.0, recommended_strike: null, recommended_expiry: null,
    bid_premium: null, annualised_yield: null, call_delta: null,
    days_to_earnings: null, composite_score: 29.5,
    recommendation_status: 'suppressed', sort_order: 10, candidates: [],
  },
];

function _makeResponse(data) {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * Return a synthetic fetch Response for demo-mode API calls.
 * Called from fetchWithAuth() in auth.js when isDemoMode() is true.
 *
 * @param {string} url - The full URL that would have been fetched
 * @returns {Response}
 */
export function demoResponse(url) {
  const u = new URL(url, window.location.origin);
  const hash = u.searchParams.get('account_hash') || '';

  if (u.pathname === '/api/accounts') {
    return _makeResponse(DEMO_ACCOUNTS);
  }
  if (u.pathname === '/api/positions/refresh') {
    return _makeResponse(
      hash === DEMO_EQUITY_HASH ? DEMO_POSITIONS_EQUITY : DEMO_POSITIONS_SPREADS
    );
  }
  if (u.pathname === '/api/screener/refresh') {
    return _makeResponse(
      hash === DEMO_EQUITY_HASH ? DEMO_SCREENER_RESULTS : []
    );
  }
  return _makeResponse({ detail: 'Demo mode: endpoint not available' });
}
