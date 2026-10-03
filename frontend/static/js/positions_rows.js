/**
 * positions_rows.js — Pure HTML builders for the positions table (specs/020 T011).
 *
 * Moved out of positions_ui.js so the markup can be tested without a browser.
 * No DOM access and no storage: every export returns an HTML string.
 */

import { adviceButton } from './quorum_ui.js';

export const COLUMN_COUNT = 14;

/**
 * Format a number as a P&L string with colour class.
 * @param {number} pnl
 * @returns {{text: string, cls: string}}
 */
export function formatPnl(pnl) {
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
export function fmt(val, decimals = 4) {
  if (val === null || val === undefined) return '—';
  return Number(val).toFixed(decimals);
}

/**
 * Get the source badge HTML for a Greek source field.
 * @param {string|null} source
 * @returns {string}
 */
export function sourceBadge(source) {
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
export function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Aggregate leg positions into a single summary row value set.
 * @param {Array<object>} legs
 * @returns {object} AggregatedRow
 */
export function aggregateLegs(legs) {
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
    underlyingPrice: sharedOrNull('underlying_price'),
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

function ivCell(p) {
  const iv = p.implied_volatility !== null && p.implied_volatility !== undefined
    ? (Number(p.implied_volatility) * 100).toFixed(1) + '%'
    : '—';
  return `<td class="px-2 py-1 text-right text-gray-200">${iv}${sourceBadge(p.iv_source)}</td>`;
}

function greekCells(p) {
  return `
      <td class="px-2 py-1 text-right text-gray-200">${fmt(p.delta, 4)}${sourceBadge(p.delta_source)}</td>
      <td class="px-2 py-1 text-right text-gray-200">${fmt(p.gamma, 4)}${sourceBadge(p.gamma_source)}</td>
      <td class="px-2 py-1 text-right text-gray-200">${fmt(p.theta, 4)}${sourceBadge(p.theta_source)}</td>
      <td class="px-2 py-1 text-right text-gray-200">${fmt(p.vega, 4)}${sourceBadge(p.vega_source)}</td>`;
}

function legBodyCells(p) {
  const pnl = formatPnl(p.unrealised_pnl);
  return `
      <td class="px-2 py-1 text-gray-300">${escapeHtml(p.underlying_symbol)}</td>
      <td class="px-2 py-1 ${p.option_type === 'call' ? 'text-green-400' : 'text-red-400'} uppercase text-xs">${escapeHtml(p.option_type)}</td>
      <td class="px-2 py-1 text-gray-200">${Number(p.strike).toFixed(2)}</td>
      <td class="px-2 py-1 text-gray-300">${escapeHtml(p.expiry_date)}</td>
      <td class="px-2 py-1 text-right ${p.quantity < 0 ? 'text-red-400' : 'text-green-400'}">${p.quantity}</td>
      <td class="px-2 py-1 text-right text-gray-200">$${Number(p.current_mark).toFixed(4)}</td>
      <td class="px-2 py-1 text-right ${pnl.cls}">${pnl.text}</td>
      <td class="px-2 py-1 text-right text-gray-400">${p.days_to_expiry}d</td>${greekCells(p)}
      ${ivCell(p)}`;
}

/** Table header: 14 columns, no Quorum column (FR-301). */
export function tableHeader() {
  const cols = [
    ['Symbol', ''], ['Underlying', ''], ['Type', ''], ['Strike', ''], ['Expiry', ''],
    ['Qty', ' text-right'], ['Mark', ' text-right'], ['P&amp;L', ' text-right'], ['DTE', ' text-right'],
    ['Delta', ' text-right'], ['Gamma', ' text-right'], ['Theta', ' text-right'], ['Vega', ' text-right'],
    ['IV', ' text-right'],
  ];
  return `<tr class="border-b border-gray-700 text-gray-500 uppercase text-xs tracking-wider">${cols
    .map(([label, cls]) => `<th class="px-2 py-1${cls}">${label}</th>`)
    .join('')}</tr>`;
}

/** One standalone option row with its ADVICE(Agentic) button after the name. */
export function standaloneRow(p) {
  return `
    <tr class="border-b border-gray-800 hover:bg-gray-900/40 transition-colors cursor-pointer"
        data-position-id="${escapeHtml(p.symbol)}">
      <td class="px-2 py-1 text-gray-200 font-mono whitespace-nowrap"><span class="pos-name">${escapeHtml(p.symbol)}</span>${adviceButton(p.symbol)}</td>${legBodyCells(p)}
    </tr>`;
}

/** A spread's summary row (with the button) followed by its hidden leg rows (no button). */
export function spreadRows(group) {
  const agg = aggregateLegs(group.legs);
  const pnl = formatPnl(agg.pnl);
  const aggCell = (key) => (agg[key] !== null
    ? fmt(agg[key], 4) + sourceBadge(agg.hasBsGreek[key] ? 'calculated' : null)
    : '—');

  const summaryRow = `
    <tr class="border-b border-gray-700 bg-gray-800/60 font-medium hover:bg-gray-700/60 transition-colors cursor-pointer" data-spread-id="${escapeHtml(group.groupId)}">
      <td class="px-2 py-1 text-gray-200 font-mono whitespace-nowrap">
        <button data-spread-toggle="${escapeHtml(group.groupId)}" class="mr-1 text-gray-400 hover:text-gray-200 transition-colors text-xs leading-none cursor-pointer">▶</button><span class="pos-name">${escapeHtml(group.groupName)}</span>${adviceButton(group.groupId)}</td>
      <td class="px-2 py-1 text-gray-300">${escapeHtml(group.underlying)}</td>
      <td class="px-2 py-1 text-gray-500">—</td>
      <td class="px-2 py-1 text-gray-500">—</td>
      <td class="px-2 py-1 text-gray-300">${escapeHtml(group.expiry)}</td>
      <td class="px-2 py-1 text-right text-gray-500">—</td>
      <td class="px-2 py-1 text-right text-gray-500">—</td>
      <td class="px-2 py-1 text-right ${pnl.cls}">${pnl.text}</td>
      <td class="px-2 py-1 text-right text-gray-400">${agg.dte !== null ? agg.dte + 'd' : '—'}</td>
      <td class="px-2 py-1 text-right text-gray-200">${aggCell('delta')}</td>
      <td class="px-2 py-1 text-right text-gray-200">${aggCell('gamma')}</td>
      <td class="px-2 py-1 text-right text-gray-200">${aggCell('theta')}</td>
      <td class="px-2 py-1 text-right text-gray-200">${aggCell('vega')}</td>
      <td class="px-2 py-1 text-right text-gray-500">—</td>
    </tr>`;

  const legRows = group.legs.map((p) => `
    <tr class="border-b border-gray-800 hover:bg-gray-900/40 transition-colors hidden" data-spread-leg="${escapeHtml(group.groupId)}">
      <td class="pl-5 pr-2 py-1 text-gray-400 font-mono text-xs">${escapeHtml(p.symbol)}</td>${legBodyCells(p)}
    </tr>`).join('');

  return summaryRow + legRows;
}
