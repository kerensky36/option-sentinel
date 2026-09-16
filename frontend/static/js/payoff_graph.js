/**
 * payoff_graph.js — SVG payoff chart rendering and DOM toggle wiring.
 *
 * Exports:
 *   initPayoffGraphToggle(container, positionData) — wires click + Escape handlers
 *   closeOpenGraph() — closes any currently open graph row
 */

import { analyzePayoff } from './payoff_math.js';

// ---------------------------------------------------------------------------
// Module state
// ---------------------------------------------------------------------------

let openGraphId = null;
let _escHandler = null;

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function _esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function _fmt(n, dec = 2) {
  if (!isFinite(n)) return n > 0 ? '+∞' : '-∞';
  const s = Math.abs(n).toFixed(dec);
  return (n >= 0 ? '+' : '-') + s;
}

/**
 * Normalise a PositionView object (from the positions array) to a PayoffLeg.
 * @param {object} pos
 * @returns {{ strike: number, optionType: string, quantity: number, cost: number }}
 */
function _toLeg(pos) {
  return {
    strike:     parseFloat(pos.strike),
    optionType: pos.option_type,
    quantity:   pos.quantity,
    cost:       parseFloat(pos.cost),
  };
}

// ---------------------------------------------------------------------------
// SVG builder
// ---------------------------------------------------------------------------

const W = 800;
const H = 180;
const PAD = { top: 24, right: 20, bottom: 36, left: 58 };
const CHART_W = W - PAD.left - PAD.right;
const CHART_H = H - PAD.top - PAD.bottom;

// Palette — dark theme, matches app
const C = {
  zero:       '#4b5563',  // gray-600
  strike:     '#6b7280',  // gray-500
  curve:      '#e5e7eb',  // gray-200
  gain:       '#4ade80',  // green-400
  loss:       '#f87171',  // red-400
  axis:       '#374151',  // gray-700
  label:      '#9ca3af',  // gray-400
  bg:         'transparent',
};
const FONT = '"JetBrains Mono", monospace';

/**
 * Map a data value to SVG x coordinate.
 */
function _xScale(price, priceMin, priceMax) {
  return PAD.left + ((price - priceMin) / (priceMax - priceMin)) * CHART_W;
}

/**
 * Map a P&L value to SVG y coordinate.
 */
function _yScale(pnl, pnlMin, pnlMax) {
  const range = pnlMax - pnlMin || 1;
  return PAD.top + CHART_H - ((pnl - pnlMin) / range) * CHART_H;
}

/**
 * Build the complete SVG string for a given set of option legs.
 *
 * @param {Array} legs - PayoffLeg array
 * @param {{ title?: string }} opts
 * @returns {string} SVG markup
 */
export function buildPayoffSvg(legs, opts = {}) {
  const title = opts.title || '';
  const analysis = analyzePayoff(legs);
  const { maxGain, maxLoss, strikePrices, curve } = analysis;

  const priceMin = curve[0].price;
  const priceMax = curve[curve.length - 1].price;
  const pnlMin   = Math.min(maxLoss,  0) * 1.15;
  const pnlMax   = Math.max(maxGain,  0) * 1.15 || 1;

  const xs = p => _xScale(p, priceMin, priceMax);
  const ys = v => _yScale(v, pnlMin, pnlMax);

  // Zero line y position
  const y0 = ys(0);

  // --- Payoff polyline ---
  const points = curve.map(pt => `${xs(pt.price).toFixed(1)},${ys(pt.pnl).toFixed(1)}`).join(' ');

  // --- Strike vertical lines ---
  const strikeLines = strikePrices.map((k, idx) => {
    const x = xs(k);
    const labelY = PAD.top + CHART_H + 18 + (idx % 2 === 0 ? 0 : 10);
    return `
    <line x1="${x.toFixed(1)}" y1="${PAD.top}" x2="${x.toFixed(1)}" y2="${(PAD.top + CHART_H).toFixed(1)}"
          stroke="${C.strike}" stroke-width="1" stroke-dasharray="4,3"/>
    <text x="${x.toFixed(1)}" y="${labelY}" text-anchor="middle"
          font-family=${FONT} font-size="9" fill="${C.strike}">$${_esc(k.toFixed(0))}</text>`;
  }).join('');

  // --- Zero line ---
  const zeroLine = `
    <line x1="${PAD.left}" y1="${y0.toFixed(1)}" x2="${(PAD.left + CHART_W).toFixed(1)}" y2="${y0.toFixed(1)}"
          stroke="${C.zero}" stroke-width="1" stroke-dasharray="6,4"/>`;

  // --- Max gain annotation ---
  const maxGainX = xs(curve.reduce((b, pt) => pt.pnl > b.pnl ? pt : b).price);
  const maxGainY = ys(maxGain);
  const gainLabel = `
    <circle cx="${maxGainX.toFixed(1)}" cy="${maxGainY.toFixed(1)}" r="3" fill="${C.gain}"/>
    <text x="${Math.min(maxGainX + 5, W - PAD.right - 45).toFixed(1)}" y="${Math.max(maxGainY - 4, PAD.top + 8).toFixed(1)}"
          font-family=${FONT} font-size="9" fill="${C.gain}">${_esc(_fmt(maxGain))}</text>`;

  // --- Max loss annotation ---
  const maxLossX = xs(curve.reduce((b, pt) => pt.pnl < b.pnl ? pt : b).price);
  const maxLossY = ys(maxLoss);
  const lossLabel = `
    <circle cx="${maxLossX.toFixed(1)}" cy="${maxLossY.toFixed(1)}" r="3" fill="${C.loss}"/>
    <text x="${Math.min(maxLossX + 5, W - PAD.right - 45).toFixed(1)}" y="${Math.min(maxLossY + 12, PAD.top + CHART_H - 4).toFixed(1)}"
          font-family=${FONT} font-size="9" fill="${C.loss}">${_esc(_fmt(maxLoss))}</text>`;

  // --- X-axis labels (5 evenly spaced prices) ---
  const xLabels = Array.from({ length: 5 }, (_, i) => {
    const price = priceMin + (i / 4) * (priceMax - priceMin);
    const x = xs(price);
    return `<text x="${x.toFixed(1)}" y="${(PAD.top + CHART_H + 12).toFixed(1)}"
            text-anchor="middle" font-family=${FONT} font-size="9" fill="${C.label}">$${_esc(price.toFixed(0))}</text>`;
  }).join('');

  // --- Y-axis labels (4 evenly spaced P&L values) ---
  const yLabels = Array.from({ length: 4 }, (_, i) => {
    const pnl = pnlMin + (i / 3) * (pnlMax - pnlMin);
    const y = ys(pnl);
    return `<text x="${(PAD.left - 4).toFixed(1)}" y="${(y + 3).toFixed(1)}"
            text-anchor="end" font-family=${FONT} font-size="9" fill="${C.label}">${_esc(_fmt(pnl))}</text>`;
  }).join('');

  // --- Axis lines ---
  const axes = `
    <line x1="${PAD.left}" y1="${PAD.top}" x2="${PAD.left}" y2="${(PAD.top + CHART_H).toFixed(1)}"
          stroke="${C.axis}" stroke-width="1"/>
    <line x1="${PAD.left}" y1="${(PAD.top + CHART_H).toFixed(1)}" x2="${(PAD.left + CHART_W).toFixed(1)}" y2="${(PAD.top + CHART_H).toFixed(1)}"
          stroke="${C.axis}" stroke-width="1"/>`;

  // --- Title ---
  const titleSvg = title
    ? `<text x="${PAD.left}" y="${PAD.top - 6}" font-family=${FONT} font-size="10" fill="${C.label}">${_esc(title)}</text>`
    : '';

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" style="width:100%;display:block;">
    <rect width="${W}" height="${H}" fill="${C.bg}"/>
    ${titleSvg}
    ${axes}
    ${zeroLine}
    ${strikeLines}
    <polyline points="${points}" fill="none" stroke="${C.curve}" stroke-width="1.5"/>
    ${gainLabel}
    ${lossLabel}
    ${xLabels}
    ${yLabels}
  </svg>`;
}

// ---------------------------------------------------------------------------
// DOM toggle
// ---------------------------------------------------------------------------

/**
 * Close any currently open graph row.
 */
export function closeOpenGraph() {
  if (openGraphId) {
    document.getElementById(openGraphId)?.remove();
    openGraphId = null;
  }
}

/**
 * Wire payoff graph toggle handlers onto the positions table.
 * SVGs are pre-computed at init time so click response is near-instant.
 *
 * @param {Element} container - The positions-table container element
 * @param {{ groups: Array, standalone: Array }} positionData
 */
export function initPayoffGraphToggle(container, positionData) {
  const { groups = [], standalone = [] } = positionData || {};

  // Remove previous Escape listener if reinitialised
  if (_escHandler) document.removeEventListener('keydown', _escHandler);
  closeOpenGraph();

  _escHandler = (e) => { if (e.key === 'Escape') closeOpenGraph(); };
  document.addEventListener('keydown', _escHandler);

  const tbody = container.querySelector('tbody');
  if (!tbody) return;

  // Pre-compute all SVGs now so clicks are instant (no computation on click path).
  const svgCache = new Map();

  for (const group of groups) {
    if (!group.legs || group.legs.length === 0) continue;
    const graphId = `payoff-${group.groupId}`;
    const legs = group.legs.map(_toLeg);
    svgCache.set(graphId, {
      svg: buildPayoffSvg(legs, { title: group.groupName || '' }),
      anchorId: group.groupId,
    });
  }

  for (const pos of standalone) {
    const graphId = `payoff-${encodeURIComponent(pos.symbol)}`;
    const legs = [_toLeg(pos)];
    svgCache.set(graphId, {
      svg: buildPayoffSvg(legs, { title: `${pos.underlying_symbol} · ${pos.expiry_date}` }),
      anchorId: pos.symbol,
    });
  }

  function _showGraph(anchorRow, graphId) {
    if (openGraphId === graphId) { closeOpenGraph(); return; }
    closeOpenGraph();

    const cached = svgCache.get(graphId);
    if (!cached) return;

    const graphRow = document.createElement('tr');
    graphRow.id = graphId;
    graphRow.className = 'payoff-graph-row';
    graphRow.innerHTML = `<td colspan="14" class="px-4 py-3 bg-gray-900/60">${cached.svg}</td>`;
    anchorRow.insertAdjacentElement('afterend', graphRow);
    openGraphId = graphId;
  }

  tbody.addEventListener('click', (e) => {
    // --- Spread group rows ---
    const spreadRow = e.target.closest('[data-spread-id]');
    if (spreadRow && !e.target.closest('[data-spread-toggle]')) {
      _showGraph(spreadRow, `payoff-${spreadRow.dataset.spreadId}`);
      return;
    }

    // --- Standalone option rows ---
    const standaloneRow = e.target.closest('[data-position-id]');
    if (standaloneRow) {
      _showGraph(standaloneRow, `payoff-${encodeURIComponent(standaloneRow.dataset.positionId)}`);
    }
  });
}
