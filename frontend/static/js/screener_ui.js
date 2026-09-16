/**
 * screener_ui.js — Covered call screener table rendering and refresh logic.
 */

import { fetchWithAuth, isAuthenticated } from './auth.js';
import { withAccountHash, getSelectedAccountHash } from './account_picker.js';
import { saveScreenerResults, loadScreenerResults, saveScreenerProfile, loadScreenerProfile } from './screener_cache.js';

const TABLE_ID = 'screener-table';
const REFRESH_BTN_ID = 'screener-refresh-btn';
const PROFILE_TOGGLE_ID = 'screener-profile-toggle';

const PROFILES = {
  conservative: { targetDelta: 0.15, dteMin: 30, dteMax: 60, yieldWeight: 0.15, safetyWeight: 0.35 },
  balanced:     { targetDelta: 0.25, dteMin: 30, dteMax: 45, yieldWeight: 0.30, safetyWeight: 0.20 },
  aggressive:   { targetDelta: 0.35, dteMin:  7, dteMax: 30, yieldWeight: 0.40, safetyWeight: 0.10 },
};

let cachedResults = [];

function rescoreResult(result, profile) {
  if (result.recommendation_status === 'suppressed') return result;
  const candidates = result.candidates;
  if (!candidates || !candidates.length) return result;
  const liquid = candidates.filter(c => c.dte >= profile.dteMin && c.dte <= profile.dteMax);
  if (!liquid.length) {
    return { ...result, recommendation_status: 'insufficient_data', composite_score: 0 };
  }
  const best = liquid.reduce((b, c) =>
    Math.abs(c.delta - profile.targetDelta) < Math.abs(b.delta - profile.targetDelta) ? c : b
  );
  const annYield = (best.bid / result.stock_price) * (365 / best.dte) * 100;
  const yieldScore = Math.min(100, annYield * 5);
  const deltaSafety = Math.max(0, 100 - Math.abs(best.delta - profile.targetDelta) * 400);
  const score = (result.iv_rank || 0) * 0.50 + yieldScore * profile.yieldWeight + deltaSafety * profile.safetyWeight;
  return {
    ...result,
    recommended_strike: best.strike,
    recommended_expiry: best.expiry,
    bid_premium: best.bid,
    annualised_yield: Math.round(annYield * 100) / 100,
    call_delta: best.delta,
    composite_score: Math.round(score * 10) / 10,
    recommendation_status: 'recommended',
  };
}

function applyProfile(results, profileOrName) {
  const profile = typeof profileOrName === 'string' ? PROFILES[profileOrName] : profileOrName;
  if (!profile) return;
  const rescored = results.map(r => rescoreResult(r, profile));
  const recommended = rescored
    .filter(r => r.recommendation_status === 'recommended')
    .sort((a, b) => b.composite_score - a.composite_score);
  const other = rescored.filter(r => r.recommendation_status !== 'recommended');
  const ordered = [...recommended, ...other].map((r, i) => ({ ...r, sort_order: i }));
  renderScreener(ordered);
}

function renderProfileToggle(activeProfile) {
  const container = document.getElementById(PROFILE_TOGGLE_ID);
  if (!container) return;
  const buttons = ['conservative', 'balanced', 'aggressive'].map(name => {
    const label = name.charAt(0).toUpperCase() + name.slice(1);
    const isActive = name === activeProfile;
    const activeClass = isActive
      ? 'bg-gray-600 text-gray-100'
      : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200';
    return `<button data-profile="${name}" class="${activeClass} px-3 py-1 text-xs uppercase tracking-wider transition-colors">${label}</button>`;
  }).join('');
  container.innerHTML = `<div class="flex gap-1">${buttons}</div>`;
  container.querySelectorAll('button[data-profile]').forEach(btn => {
    btn.addEventListener('click', () => {
      const name = btn.dataset.profile;
      saveScreenerProfile(name);
      renderProfileToggle(name);
      _syncSlidersToProfile(PROFILES[name]);
      applyProfile(cachedResults, name);
    });
  });
}

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
      return '<span class="bg-green-900 text-green-300 px-1.5 py-0.5 uppercase tracking-wider text-xs">Recommended</span>';
    case 'suppressed':
      return '<span class="bg-amber-900 text-amber-300 px-1.5 py-0.5 uppercase tracking-wider text-xs">Suppressed</span>';
    case 'insufficient_data':
    default:
      return '<span class="bg-gray-800 text-gray-500 px-1.5 py-0.5 uppercase tracking-wider text-xs">No Data</span>';
  }
}

function _syncSlidersToProfile(profile) {
  const deltaSlider = document.getElementById('screener-delta-slider');
  const dteSlider = document.getElementById('screener-dte-slider');
  const yieldSlider = document.getElementById('screener-yield-weight-slider');
  if (!deltaSlider) return;
  const dteMid = Math.round((profile.dteMin + profile.dteMax) / 2);
  deltaSlider.value = profile.targetDelta;
  dteSlider.value = dteMid;
  yieldSlider.value = Math.round(profile.yieldWeight * 200);
  document.getElementById('screener-delta-label').textContent = Number(profile.targetDelta).toFixed(2);
  document.getElementById('screener-dte-label').textContent = dteMid + 'd';
  document.getElementById('screener-yield-weight-label').textContent = Math.round(profile.yieldWeight * 200) + '%';
}

function initAdvancedSliders() {
  const deltaSlider = document.getElementById('screener-delta-slider');
  const dteSlider = document.getElementById('screener-dte-slider');
  const yieldSlider = document.getElementById('screener-yield-weight-slider');
  if (!deltaSlider) return;

  const activeProfile = PROFILES[loadScreenerProfile()] || PROFILES.balanced;
  _syncSlidersToProfile(activeProfile);

  function onSliderInput() {
    const dteMid = parseInt(dteSlider.value, 10);
    const sv = parseInt(yieldSlider.value, 10);
    const customProfile = {
      targetDelta: parseFloat(deltaSlider.value),
      dteMin: Math.max(7, dteMid - 10),
      dteMax: Math.min(60, dteMid + 10),
      yieldWeight: sv / 200,
      safetyWeight: (100 - sv) / 200,
    };
    document.getElementById('screener-delta-label').textContent = customProfile.targetDelta.toFixed(2);
    document.getElementById('screener-dte-label').textContent = dteMid + 'd';
    document.getElementById('screener-yield-weight-label').textContent = sv + '%';
    applyProfile(cachedResults, customProfile);
  }

  deltaSlider.addEventListener('input', onSliderInput);
  dteSlider.addEventListener('input', onSliderInput);
  yieldSlider.addEventListener('input', onSliderInput);
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
      <div class="text-gray-500 text-center py-8 text-sm">
        No screener results. Click <strong>Refresh</strong> to fetch live data.
      </div>`;
    return;
  }

  const rows = results.map((r) => `
    <tr class="border-b border-gray-800 hover:bg-gray-900\/40 transition-colors ${r.recommendation_status === 'suppressed' ? 'opacity-60' : ''}">
      <td class="px-2 py-1 text-gray-200 font-mono">${r.ticker}</td>
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
          <tr class="border-b border-gray-700 text-gray-500 uppercase text-xs tracking-wider">
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
    saveScreenerResults(results, getSelectedAccountHash());
    cachedResults = results;
    renderProfileToggle(loadScreenerProfile());
    initAdvancedSliders();
    applyProfile(cachedResults, loadScreenerProfile());
  } catch (err) {
    console.error('screener_ui: refresh failed', err);
    const container = document.getElementById(TABLE_ID);
    if (container) {
      container.innerHTML = `
        <div class="text-red-400 text-center py-4 text-sm">
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
 * Handle account selection: load account-scoped cache or fetch fresh data.
 * @param {string} accountHash
 */
async function handleAccountChange(accountHash) {
  const cached = loadScreenerResults(accountHash);
  if (cached !== null) {
    cachedResults = cached;
    renderProfileToggle(loadScreenerProfile());
    initAdvancedSliders();
    applyProfile(cachedResults, loadScreenerProfile());
    return;
  }
  await refreshScreener();
}

/**
 * Initialise: wire up Refresh button and wait for account to resolve.
 * Data is fetched/rendered once the accountchange event fires.
 */
function init() {
  const btn = document.getElementById(REFRESH_BTN_ID);
  if (btn) {
    btn.addEventListener('click', refreshScreener);
  }
  document.addEventListener('accountchange', (e) => {
    handleAccountChange(e.detail.accountHash);
  });
}

init();
