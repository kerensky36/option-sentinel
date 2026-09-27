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
import { initPayoffGraphToggle, closeOpenGraph } from './payoff_graph.js';
import { initQuorum } from './quorum_ui.js';
import { tableHeader, standaloneRow, spreadRows as buildSpreadRows } from './positions_rows.js';

const TABLE_ID = 'positions-table';
const TIMESTAMP_ID = 'positions-timestamp';
const REFRESH_BTN_ID = 'positions-refresh-btn';

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

  const { groups, standalone } = buildSpreadGroups(positions);

  const spreadRows = groups.map(buildSpreadRows).join('');
  const standaloneRows = standalone.map(standaloneRow).join('');

  container.innerHTML = `
    <div class="overflow-x-auto">
      <table class="w-full text-left">
        <thead>
          ${tableHeader()}
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

  // Macro news voting quorum buttons (specs/017)
  initQuorum(container, { groups, standalone });

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
