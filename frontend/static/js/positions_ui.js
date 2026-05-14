/**
 * positions_ui.js — Positions table rendering and refresh logic.
 *
 * On page load: reads cached positions from IndexedDB and renders immediately.
 * On Refresh button click: fetches live data from /api/positions/refresh,
 * caches result, then re-renders.
 */

import { fetchWithAuth, isAuthenticated } from './auth.js';
import { savePositions, loadPositions } from './position_cache.js';
import { getAssignments } from './thesis_store.js';

const TABLE_ID = 'positions-table';
const TIMESTAMP_ID = 'positions-timestamp';
const REFRESH_BTN_ID = 'positions-refresh-btn';

/**
 * Format a number as a P&L string with colour class.
 * @param {number} pnl
 * @returns {{text: string, cls: string}}
 */
function formatPnl(pnl) {
  const n = Number(pnl);
  const abs = Math.abs(n).toFixed(2);
  return {
    text: (n >= 0 ? '+' : '-') + '$' + abs,
    cls: n >= 0 ? 'text-green-400' : 'text-red-400',
  };
}

/**
 * Format a Greek value for display.
 * @param {number|null} val
 * @param {number} decimals
 * @returns {string}
 */
function fmt(val, decimals = 4) {
  if (val === null || val === undefined) return '—';
  return Number(val).toFixed(decimals);
}

/**
 * Get the source badge HTML for a Greek source field.
 * @param {string|null} source
 * @returns {string}
 */
function sourceBadge(source) {
  if (!source) return '';
  if (source === 'calculated') {
    return '<span class="ml-0.5 text-amber-400" title="Black-Scholes estimate" style="font-size:9px">BS</span>';
  }
  return '';
}

/**
 * Render a positions array into the positions table.
 * @param {Array<object>} positions
 * @param {string|null} timestamp - ISO string of last refresh time.
 */
export function renderPositions(positions, timestamp) {
  const container = document.getElementById(TABLE_ID);
  if (!container) return;

  const assignments = getAssignments();
  const assignMap = {};
  for (const a of assignments) {
    assignMap[a.symbol] = a.thesis_group_id;
  }

  if (!positions || positions.length === 0) {
    container.innerHTML = `
      <div class="text-gray-500 text-center py-8" style="font-size:12px">
        No open positions. Click <strong>Refresh</strong> to fetch live data.
      </div>`;
    return;
  }

  const rows = positions.map((p) => {
    const pnl = formatPnl(p.unrealised_pnl);
    const thesisId = assignMap[p.symbol];
    const thesisBadge = thesisId
      ? `<span class="bg-indigo-900\/60 text-indigo-300 border border-indigo-800 px-1" style="font-size:10px">${thesisId}</span>`
      : '';

    return `
    <tr class="border-b border-gray-800 hover:bg-gray-900\/40 transition-colors">
      <td class="px-2 py-1 text-gray-200 font-mono" style="font-size:11px">${p.symbol}</td>
      <td class="px-2 py-1 text-gray-300">${p.underlying_symbol}</td>
      <td class="px-2 py-1 ${p.option_type === 'call' ? 'text-green-400' : 'text-red-400'} uppercase" style="font-size:10px">${p.option_type}</td>
      <td class="px-2 py-1 text-gray-200">${Number(p.strike).toFixed(2)}</td>
      <td class="px-2 py-1 text-gray-300">${p.expiry_date}</td>
      <td class="px-2 py-1 text-right ${p.quantity < 0 ? 'text-red-400' : 'text-green-400'}">${p.quantity}</td>
      <td class="px-2 py-1 text-right text-gray-200">$${Number(p.current_mark).toFixed(4)}</td>
      <td class="px-2 py-1 text-right ${pnl.cls}">${pnl.text}</td>
      <td class="px-2 py-1 text-right text-gray-400">${p.days_to_expiry}d</td>
      <td class="px-2 py-1 text-right text-gray-200">${fmt(p.delta, 4)}${sourceBadge(p.delta_source)}</td>
      <td class="px-2 py-1 text-right text-gray-200">${fmt(p.gamma, 4)}${sourceBadge(p.gamma_source)}</td>
      <td class="px-2 py-1 text-right text-gray-200">${fmt(p.theta, 4)}${sourceBadge(p.theta_source)}</td>
      <td class="px-2 py-1 text-right text-gray-200">${fmt(p.vega, 4)}${sourceBadge(p.vega_source)}</td>
      <td class="px-2 py-1 text-right text-gray-200">${p.implied_volatility !== null && p.implied_volatility !== undefined ? (Number(p.implied_volatility) * 100).toFixed(1) + '%' : '—'}${sourceBadge(p.iv_source)}</td>
      <td class="px-2 py-1">${thesisBadge}</td>
    </tr>`;
  }).join('');

  container.innerHTML = `
    <div class="overflow-x-auto">
      <table class="w-full text-left">
        <thead>
          <tr class="border-b border-gray-700 text-gray-500 uppercase" style="font-size:10px; letter-spacing:0.10em;">
            <th class="px-2 py-1">Symbol</th>
            <th class="px-2 py-1">Underlying</th>
            <th class="px-2 py-1">Type</th>
            <th class="px-2 py-1">Strike</th>
            <th class="px-2 py-1">Expiry</th>
            <th class="px-2 py-1 text-right">Qty</th>
            <th class="px-2 py-1 text-right">Mark</th>
            <th class="px-2 py-1 text-right">P&L</th>
            <th class="px-2 py-1 text-right">DTE</th>
            <th class="px-2 py-1 text-right">Delta</th>
            <th class="px-2 py-1 text-right">Gamma</th>
            <th class="px-2 py-1 text-right">Theta</th>
            <th class="px-2 py-1 text-right">Vega</th>
            <th class="px-2 py-1 text-right">IV</th>
            <th class="px-2 py-1">Thesis</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;

  // Update timestamp badge
  const tsEl = document.getElementById(TIMESTAMP_ID);
  if (tsEl && timestamp) {
    const d = new Date(timestamp);
    tsEl.textContent = 'Last refreshed: ' + d.toLocaleTimeString();
    tsEl.classList.remove('hidden');
  }
}

/**
 * Fetch positions from the server and update the cache + table.
 */
async function refreshPositions() {
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
    const resp = await fetchWithAuth('/api/positions/refresh');

    if (!resp) return; // eraseAll() already called by fetchWithAuth on 401

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    }

    const positions = await resp.json();
    const timestamp = new Date().toISOString();
    await savePositions(positions);
    renderPositions(positions, timestamp);
  } catch (err) {
    console.error('positions_ui: refresh failed', err);
    const container = document.getElementById(TABLE_ID);
    if (container) {
      container.innerHTML = `
        <div class="text-red-400 text-center py-4" style="font-size:12px">
          Failed to refresh positions: ${err.message}
          <button id="${REFRESH_BTN_ID}" class="ml-3 bg-gray-800 hover:bg-gray-700 text-gray-300 px-2 py-0.5 uppercase tracking-wider" style="font-size:10px">Retry</button>
        </div>`;
      document.getElementById(REFRESH_BTN_ID)?.addEventListener('click', refreshPositions);
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Refresh';
    }
  }
}

/**
 * Initialise: load cached positions immediately, wire up Refresh button.
 * Auto-fetches live data on first visit when no cache exists.
 */
async function init() {
  let hasCached = false;

  try {
    const cached = await loadPositions();
    if (cached) {
      hasCached = true;
      renderPositions(cached.positions, cached.savedAt);
    }
  } catch (e) {
    console.warn('positions_ui: cache load failed', e);
  }

  const btn = document.getElementById(REFRESH_BTN_ID);
  if (btn) {
    btn.addEventListener('click', refreshPositions);
  }

  if (!hasCached) {
    await refreshPositions();
  }
}

init();
