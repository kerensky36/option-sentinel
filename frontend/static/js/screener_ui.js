/**
 * screener_ui.js — Covered call screener table rendering and refresh logic.
 */

import { fetchWithAuth, isAuthenticated } from './auth.js';
import { withAccountHash } from './account_picker.js';

const TABLE_ID = 'screener-table';
const REFRESH_BTN_ID = 'screener-refresh-btn';

/**
 * Format a float value for display.
 * @param {number|null} val
 * @param {number} decimals
 * @returns {string}
 */
function fmt(val, decimals = 2) {
  if (val === null || val === undefined) return '—';
  return Number(val).toFixed(decimals);
}

/**
 * Get the status badge HTML for a recommendation status.
 * @param {string} status
 * @returns {string}
 */
function statusBadge(status) {
  switch (status) {
    case 'recommended':
      return '<span class="bg-green-900 text-green-300 px-1.5 py-0.5 uppercase tracking-wider" style="font-size:9px; border-radius:1px">Recommended</span>';
    case 'suppressed':
      return '<span class="bg-amber-900 text-amber-300 px-1.5 py-0.5 uppercase tracking-wider" style="font-size:9px; border-radius:1px">Suppressed</span>';
    case 'insufficient_data':
    default:
      return '<span class="bg-gray-800 text-gray-500 px-1.5 py-0.5 uppercase tracking-wider" style="font-size:9px; border-radius:1px">No Data</span>';
  }
}

/**
 * Render the screener results into the table container.
 * @param {Array<object>} results
 */
export function renderScreener(results) {
  const container = document.getElementById(TABLE_ID);
  if (!container) return;

  if (!results || results.length === 0) {
    container.innerHTML = `
      <div class="text-gray-500 text-center py-8" style="font-size:12px">
        No screener results. Click <strong>Refresh</strong> to fetch live data.
      </div>`;
    return;
  }

  const rows = results.map((r) => `
    <tr class="border-b border-gray-800 hover:bg-gray-900\/40 transition-colors ${r.recommendation_status === 'suppressed' ? 'opacity-60' : ''}">
      <td class="px-2 py-1 text-gray-200 font-mono" style="font-size:11px">${r.ticker}</td>
      <td class="px-2 py-1 text-right text-gray-300">${r.shares.toLocaleString()}</td>
      <td class="px-2 py-1 text-right text-gray-200">$${fmt(r.stock_price)}</td>
      <td class="px-2 py-1 text-right text-gray-200">${r.iv_rank !== null && r.iv_rank !== undefined ? fmt(r.iv_rank, 1) : '—'}</td>
      <td class="px-2 py-1 text-right text-gray-200">${r.recommended_strike !== null && r.recommended_strike !== undefined ? '$' + fmt(r.recommended_strike) : '—'}</td>
      <td class="px-2 py-1 text-gray-300">${r.recommended_expiry || '—'}</td>
      <td class="px-2 py-1 text-right text-gray-200">${r.bid_premium !== null && r.bid_premium !== undefined ? '$' + fmt(r.bid_premium, 2) : '—'}</td>
      <td class="px-2 py-1 text-right ${r.annualised_yield ? 'text-green-400' : 'text-gray-400'}">${r.annualised_yield !== null && r.annualised_yield !== undefined ? fmt(r.annualised_yield, 1) + '%' : '—'}</td>
      <td class="px-2 py-1 text-right text-gray-200">${r.call_delta !== null && r.call_delta !== undefined ? fmt(r.call_delta, 3) : '—'}</td>
      <td class="px-2 py-1 text-right text-gray-300">${r.days_to_earnings !== null && r.days_to_earnings !== undefined ? r.days_to_earnings + 'd' : '—'}</td>
      <td class="px-2 py-1 text-right text-gray-200">${fmt(r.composite_score, 1)}</td>
      <td class="px-2 py-1">${statusBadge(r.recommendation_status)}</td>
    </tr>`).join('');

  container.innerHTML = `
    <div class="overflow-x-auto">
      <table class="w-full text-left">
        <thead>
          <tr class="border-b border-gray-700 text-gray-500 uppercase" style="font-size:10px; letter-spacing:0.10em;">
            <th class="px-2 py-1">Ticker</th>
            <th class="px-2 py-1 text-right">Shares</th>
            <th class="px-2 py-1 text-right">Price</th>
            <th class="px-2 py-1 text-right">IV Rank</th>
            <th class="px-2 py-1 text-right">Strike</th>
            <th class="px-2 py-1">Expiry</th>
            <th class="px-2 py-1 text-right">Bid</th>
            <th class="px-2 py-1 text-right">Ann. Yield</th>
            <th class="px-2 py-1 text-right">Delta</th>
            <th class="px-2 py-1 text-right">DTE Earn.</th>
            <th class="px-2 py-1 text-right">Score</th>
            <th class="px-2 py-1">Status</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

/**
 * Fetch screener results from the server and render.
 */
async function refreshScreener() {
  if (!isAuthenticated()) {
    window.location.replace('/auth/login');
    return;
  }

  const btn = document.getElementById(REFRESH_BTN_ID);
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Refreshing…';
  }

  try {
    const resp = await fetchWithAuth(withAccountHash('/api/screener/refresh'));

    if (!resp) return; // eraseAll() already called by fetchWithAuth on 401

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    }

    const results = await resp.json();
    renderScreener(results);
  } catch (err) {
    console.error('screener_ui: refresh failed', err);
    const container = document.getElementById(TABLE_ID);
    if (container) {
      container.innerHTML = `
        <div class="text-red-400 text-center py-4" style="font-size:12px">
          Failed to refresh screener: ${err.message}
        </div>`;
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Refresh';
    }
  }
}

/**
 * Initialise: wire up Refresh button and auto-fetch on first visit.
 */
async function init() {
  const btn = document.getElementById(REFRESH_BTN_ID);
  if (btn) {
    btn.addEventListener('click', refreshScreener);
  }
  await refreshScreener();
}

init();
