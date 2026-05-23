/**
 * positions_ui.js — Positions table rendering and refresh logic.
 *
 * On page load: reads cached positions from sessionStorage and renders immediately.
 * On Refresh button click: fetches live data from /api/positions/refresh,
 * caches result, then re-renders.
 */

import { fetchWithAuth, isAuthenticated } from './auth.js';
import { withAccountHash, getSelectedAccountHash } from './account_picker.js';
import { savePositions, loadPositions } from './position_cache.js';
import { getAssignments } from './thesis_store.js';
import { initPayoffGraphToggle, closeOpenGraph } from './payoff_graph.js';

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
    return '<span class="ml-0.5 text-amber-400 text-xs" title="Black-Scholes estimate">BS</span>';
  }
  return '';
}

/**
 * Escape HTML special characters to prevent XSS.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Group positions into spread groups by (underlying_symbol, expiry_date).
 * Any underlying+expiry pair with 2+ legs forms a collapsible group.
 * @param {Array<object>} positions
 * @returns {{ groups: Array<object>, standalone: Array<object> }}
 */
function buildSpreadGroups(positions) {
  const groupMap = {};
  for (const p of positions) {
    const groupKey = encodeURIComponent(p.underlying_symbol + '|' + p.expiry_date);
    if (!groupMap[groupKey]) {
      groupMap[groupKey] = {
        groupId: groupKey,
        groupName: p.underlying_symbol + ' · ' + p.expiry_date,
        underlying: p.underlying_symbol,
        expiry: p.expiry_date,
        legs: [],
        isExpanded: false,
      };
    }
    groupMap[groupKey].legs.push(p);
  }

  const groups = Object.values(groupMap).filter((g) => g.legs.length >= 2);
  const groupedSymbols = new Set(groups.flatMap((g) => g.legs.map((l) => l.symbol)));
  const standalone = positions.filter((p) => !groupedSymbols.has(p.symbol));

  return { groups, standalone };
}

/**
 * Aggregate leg positions into a single summary row value set.
 * @param {Array<object>} legs
 * @returns {object} AggregatedRow
 */
function aggregateLegs(legs) {
  const sumGreek = (key) => {
    const vals = legs.map((l) => l[key]).filter((v) => v !== null && v !== undefined);
    return vals.length ? vals.reduce((a, b) => a + b, 0) : null;
  };

  const hasBsGreek = (key) => legs.some((l) => l[`${key}_source`] === 'calculated');

  const sharedOrNull = (key) => {
    const vals = [...new Set(legs.map((l) => l[key]))];
    return vals.length === 1 ? vals[0] : null;
  };

  return {
    pnl: legs.reduce((a, l) => a + Number(l.unrealised_pnl), 0),
    underlying: sharedOrNull('underlying_symbol'),
    expiry: sharedOrNull('expiry_date'),
    dte: sharedOrNull('days_to_expiry'),
    delta: sumGreek('delta'),
    gamma: sumGreek('gamma'),
    theta: sumGreek('theta'),
    vega: sumGreek('vega'),
    hasBsGreek: {
      delta: hasBsGreek('delta'),
      gamma: hasBsGreek('gamma'),
      theta: hasBsGreek('theta'),
      vega: hasBsGreek('vega'),
    },
  };
}

/**
 * Render a positions array into the positions table.
 * @param {Array<object>} positions
 * @param {string|null} timestamp - ISO string of last refresh time.
 */
export function renderPositions(positions, timestamp) {
  const container = document.getElementById(TABLE_ID);
  if (!container) return;

  closeOpenGraph();

  if (!positions || positions.length === 0) {
    container.innerHTML = `
      <div class="text-gray-500 text-center py-8 text-sm">
        No open positions. Click <strong>Refresh</strong> to fetch live data.
      </div>`;
    return;
  }

  const assignments = getAssignments();
  const assignMap = Object.fromEntries(assignments.filter((a) => a.thesis_group_id).map((a) => [a.symbol, a.thesis_group_id]));
  const { groups, standalone } = buildSpreadGroups(positions);

  const renderLegRow = (p) => {
    const pnl = formatPnl(p.unrealised_pnl);
    const thesisId = assignMap[p.symbol];
    const thesisBadge = thesisId
      ? `<span class="bg-indigo-900\/60 text-indigo-300 border border-indigo-800 px-1 text-xs">${thesisId}</span>`
      : '';
    return `
    <tr class="border-b border-gray-800 hover:bg-gray-900\/40 transition-colors cursor-pointer"
        data-position-id="${escapeHtml(p.symbol)}">
      <td class="px-2 py-1 text-gray-200 font-mono">${p.symbol}</td>
      <td class="px-2 py-1 text-gray-300">${p.underlying_symbol}</td>
      <td class="px-2 py-1 ${p.option_type === 'call' ? 'text-green-400' : 'text-red-400'} uppercase text-xs">${p.option_type}</td>
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
  };

  const renderSpreadRows = (group) => {
    const agg = aggregateLegs(group.legs);
    const pnl = formatPnl(agg.pnl);

    const summaryRow = `
    <tr class="border-b border-gray-700 bg-gray-800\/60 font-medium" data-spread-id="${group.groupId}">
      <td class="px-2 py-1 text-gray-200 font-mono">
        <button data-spread-toggle="${group.groupId}" class="mr-1 text-gray-400 hover:text-gray-200 transition-colors text-xs leading-none cursor-pointer">▶</button>${escapeHtml(group.groupName)}
      </td>
      <td class="px-2 py-1 text-gray-300">${group.underlying}</td>
      <td class="px-2 py-1 text-gray-500">—</td>
      <td class="px-2 py-1 text-gray-500">—</td>
      <td class="px-2 py-1 text-gray-300">${group.expiry}</td>
      <td class="px-2 py-1 text-right text-gray-500">—</td>
      <td class="px-2 py-1 text-right text-gray-500">—</td>
      <td class="px-2 py-1 text-right ${pnl.cls}">${pnl.text}</td>
      <td class="px-2 py-1 text-right text-gray-400">${agg.dte !== null ? agg.dte + 'd' : '—'}</td>
      <td class="px-2 py-1 text-right text-gray-200">${agg.delta !== null ? fmt(agg.delta, 4) + sourceBadge(agg.hasBsGreek.delta ? 'calculated' : null) : '—'}</td>
      <td class="px-2 py-1 text-right text-gray-200">${agg.gamma !== null ? fmt(agg.gamma, 4) + sourceBadge(agg.hasBsGreek.gamma ? 'calculated' : null) : '—'}</td>
      <td class="px-2 py-1 text-right text-gray-200">${agg.theta !== null ? fmt(agg.theta, 4) + sourceBadge(agg.hasBsGreek.theta ? 'calculated' : null) : '—'}</td>
      <td class="px-2 py-1 text-right text-gray-200">${agg.vega !== null ? fmt(agg.vega, 4) + sourceBadge(agg.hasBsGreek.vega ? 'calculated' : null) : '—'}</td>
      <td class="px-2 py-1 text-right text-gray-500">—</td>
      <td class="px-2 py-1"></td>
    </tr>`;

    const legRows = group.legs.map((p) => {
      const pnl = formatPnl(p.unrealised_pnl);
      return `
    <tr class="border-b border-gray-800 hover:bg-gray-900\/40 transition-colors hidden" data-spread-leg="${group.groupId}">
      <td class="pl-5 pr-2 py-1 text-gray-400 font-mono text-xs">${p.symbol}</td>
      <td class="px-2 py-1 text-gray-300">${p.underlying_symbol}</td>
      <td class="px-2 py-1 ${p.option_type === 'call' ? 'text-green-400' : 'text-red-400'} uppercase text-xs">${p.option_type}</td>
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
      <td class="px-2 py-1"></td>
    </tr>`;
    }).join('');

    return summaryRow + legRows;
  };

  const spreadRows = groups.map(renderSpreadRows).join('');
  const standaloneRows = standalone.map(renderLegRow).join('');

  container.innerHTML = `
    <div class="overflow-x-auto">
      <table class="w-full text-left">
        <thead>
          <tr class="border-b border-gray-700 text-gray-500 uppercase text-xs tracking-wider">
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
        <tbody>${spreadRows}${standaloneRows}</tbody>
      </table>
    </div>`;

  // Chevron-only toggle: only [data-spread-toggle] buttons trigger expand/collapse (FR-003)
  container.querySelector('tbody')?.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-spread-toggle]');
    if (!btn) return;
    e.stopPropagation();
    const id = btn.getAttribute('data-spread-toggle');
    const isExpanded = btn.textContent.trim() === '▼';
    container.querySelectorAll(`[data-spread-leg="${id}"]`).forEach((row) => {
      row.classList.toggle('hidden', isExpanded);
    });
    btn.textContent = isExpanded ? '▶' : '▼';
  });

  // Payoff graph toggle: wires spread group rows + standalone option rows
  initPayoffGraphToggle(container, { groups, standalone });

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
    const resp = await fetchWithAuth(withAccountHash('/api/positions/refresh'));

    if (!resp) return; // eraseAll() already called by fetchWithAuth on 401

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    }

    const positions = await resp.json();
    const timestamp = new Date().toISOString();
    savePositions(positions, getSelectedAccountHash());
    renderPositions(positions, timestamp);
  } catch (err) {
    console.error('positions_ui: refresh failed', err);
    const container = document.getElementById(TABLE_ID);
    if (container) {
      container.innerHTML = `
        <div class="text-red-400 text-center py-4 text-sm">
          Failed to refresh positions: ${err.message}
          <button id="${REFRESH_BTN_ID}" class="ml-3 bg-gray-800 hover:bg-gray-700 text-gray-300 px-2 py-0.5 uppercase tracking-wider text-xs">Retry</button>
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
 * Handle account selection: load account-scoped cache or fetch fresh data.
 * @param {string} accountHash
 */
function handleAccountChange(accountHash) {
  const cached = loadPositions(accountHash);
  if (cached) {
    renderPositions(cached.positions, cached.savedAt);
    return;
  }
  refreshPositions();
}

/**
 * Initialise: wire up Refresh button and wait for account to resolve.
 * Data is fetched/rendered once the accountchange event fires.
 */
function init() {
  const btn = document.getElementById(REFRESH_BTN_ID);
  if (btn) {
    btn.addEventListener('click', refreshPositions);
  }
  document.addEventListener('accountchange', (e) => {
    handleAccountChange(e.detail.accountHash);
  });
}

init();
