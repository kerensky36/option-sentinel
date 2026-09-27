/**
 * payoff_graph.js — SVG payoff chart rendering and DOM toggle wiring.
 *
 * Exports:
 *   initPayoffGraphToggle(container, positionData) — wires click + Escape handlers
 *   closeOpenGraph() — closes any currently open graph row
 */

import { analyzePayoff, combinedPayoff } from './payoff_math.js';
import { CHECKPOINTS, availableCheckpoints, computeCheckpointCurve, combinedTheoreticalPayoff, isEligibleForOverlay } from './payoff_theoretical.js';

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
    strike:            parseFloat(pos.strike),
    optionType:        pos.option_type,
    quantity:          pos.quantity,
    cost:              parseFloat(pos.cost),
    impliedVolatility: pos.implied_volatility,
    daysToExpiry:      pos.days_to_expiry,
    underlyingPrice:   pos.underlying_price !== null && pos.underlying_price !== undefined
                          ? parseFloat(pos.underlying_price)
                          : null,
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
  curve:      '#e5e7eb',  // gray-200 — the Expiration reference curve (specs/015, unchanged)
  today:      '#60a5fa',  // blue-400 — the checkpoint-controlled curve (016)
  marker:     '#facc15',  // yellow-400 — current underlying price marker (016)
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

/**
 * Build the payoff SVG with the T+0 overlay: the existing Expiration curve
 * (buildPayoffSvg, unchanged) as a fixed reference, plus a second curve
 * reflecting whichever checkpoint is selected (defaults to "today").
 *
 * Falls back to buildPayoffSvg verbatim when the position is ineligible
 * (missing/zero IV on any leg, or zero days to expiry — FR-008, and the
 * zero-DTE edge case in spec.md).
 *
 * @param {Array} legs - PayoffLeg array, extended with impliedVolatility/daysToExpiry
 * @param {{ title?: string }} opts
 * @param {string} [checkpointId] - which CHECKPOINTS entry to draw as the second curve
 * @returns {string} SVG markup
 */
export function buildOverlaySvg(legs, opts = {}, checkpointId = 'today') {
  const baseSvg = buildPayoffSvg(legs, opts);
  if (!isEligibleForOverlay(legs)) return baseSvg;

  const analysis = analyzePayoff(legs);
  const { maxGain, maxLoss, curve } = analysis;
  const priceMin = curve[0].price;
  const priceMax = curve[curve.length - 1].price;
  const pnlMin = Math.min(maxLoss, 0) * 1.15;
  const pnlMax = Math.max(maxGain, 0) * 1.15 || 1;
  const xs = (p) => _xScale(p, priceMin, priceMax);
  const ys = (v) => _yScale(v, pnlMin, pnlMax);

  const checkpoint = CHECKPOINTS.find((c) => c.id === checkpointId) || CHECKPOINTS[0];
  const checkpointCurve = computeCheckpointCurve(legs, checkpoint, curve);
  const checkpointPoints = checkpointCurve
    .map((pt) => `${xs(pt.price).toFixed(1)},${ys(pt.pnl).toFixed(1)}`)
    .join(' ');

  const legend = `
    <text x="${(W - PAD.right - 72).toFixed(1)}" y="${(PAD.top - 6).toFixed(1)}" text-anchor="end"
          font-family=${FONT} font-size="9" fill="${C.curve}">— Expiration</text>
    <text x="${(W - PAD.right).toFixed(1)}" y="${(PAD.top - 6).toFixed(1)}" text-anchor="end"
          font-family=${FONT} font-size="9" fill="${C.today}">— ${_esc(checkpoint.label)}</text>`;

  const checkpointCurveSvg = `
    <polyline points="${checkpointPoints}" fill="none" stroke="${C.today}" stroke-width="1.5"/>`;

  const markerSvg = _buildMarkerSvg(legs, checkpoint, xs, ys);

  return baseSvg.replace('</svg>', `${legend}${checkpointCurveSvg}${markerSvg}</svg>`);
}

/**
 * Vertical marker at the current underlying price (when known), labeled with
 * both the Expiration reference curve's P&L and the checkpoint-controlled
 * curve's P&L at that exact price — evaluated directly, not read off the
 * 200-point grid (FR-006, FR-007). Styled like the existing max-gain/max-loss
 * annotations (circle + text) for visual consistency.
 * @param {Array} legs
 * @param {{label:string, offsetDays:number|null}} checkpoint
 * @param {(price:number)=>number} xs
 * @param {(pnl:number)=>number} ys
 * @returns {string}
 */
function _buildMarkerSvg(legs, checkpoint, xs, ys) {
  const underlyingPrice = legs[0].underlyingPrice;
  if (underlyingPrice === null || underlyingPrice === undefined || Number.isNaN(underlyingPrice)) {
    return '';
  }

  const referencePnl = combinedPayoff(legs, underlyingPrice);
  const checkpointPnl = checkpoint.offsetDays === null
    ? referencePnl
    : combinedTheoreticalPayoff(legs, underlyingPrice, legs[0].daysToExpiry - checkpoint.offsetDays);

  const mx = xs(underlyingPrice);
  const dotRefY = ys(referencePnl);
  const dotCkpY = ys(checkpointPnl);

  // Anchor labels to where the dots actually land (not a fixed offset from
  // the chart top) — a fixed offset collided with the legend and the
  // existing max-gain/max-loss annotation whenever the current price sat
  // near the top of the plotted range. Flip the label side when there
  // isn't room on the right, mirroring the gain/loss label clamp pattern.
  const onRight = mx < W - PAD.right - 80;
  const labelX = onRight ? mx + 6 : mx - 6;
  const anchor = onRight ? 'start' : 'end';

  // Keep the two labels from overlapping each other when the two P&L
  // values are close together, and keep both inside the plotted area.
  const MIN_GAP = 11;
  let refY = dotRefY;
  let ckpY = dotCkpY;
  if (Math.abs(refY - ckpY) < MIN_GAP) {
    const mid = (refY + ckpY) / 2;
    const spread = MIN_GAP / 2;
    if (refY <= ckpY) { refY = mid - spread; ckpY = mid + spread; }
    else { refY = mid + spread; ckpY = mid - spread; }
  }
  const clampY = (y) => Math.min(Math.max(y, PAD.top + 8), PAD.top + CHART_H - 4);
  refY = clampY(refY);
  ckpY = clampY(ckpY);

  return `
    <line x1="${mx.toFixed(1)}" y1="${PAD.top}" x2="${mx.toFixed(1)}" y2="${(PAD.top + CHART_H).toFixed(1)}"
          stroke="${C.marker}" stroke-width="1" stroke-dasharray="2,3"/>
    <circle cx="${mx.toFixed(1)}" cy="${dotRefY.toFixed(1)}" r="2.5" fill="${C.curve}"/>
    <circle cx="${mx.toFixed(1)}" cy="${dotCkpY.toFixed(1)}" r="2.5" fill="${C.today}"/>
    <text x="${labelX.toFixed(1)}" y="${(refY + 3).toFixed(1)}" text-anchor="${anchor}"
          font-family=${FONT} font-size="9" fill="${C.curve}">Exp ${_esc(_fmt(referencePnl))}</text>
    <text x="${labelX.toFixed(1)}" y="${(ckpY + 3).toFixed(1)}" text-anchor="${anchor}"
          font-family=${FONT} font-size="9" fill="${C.today}">${_esc(checkpoint.label)} ${_esc(_fmt(checkpointPnl))}</text>`;
}

/**
 * Build the "view as of" checkpoint button row. Unavailable checkpoints
 * (FR-004) render disabled rather than being omitted, so their existence
 * (and why they're greyed out — near expiration) stays visible.
 * @param {number} daysToExpiry
 * @param {string} activeId
 * @returns {string}
 */
function _buildCheckpointButtonsHtml(daysToExpiry, activeId) {
  const available = new Set(availableCheckpoints(daysToExpiry).map((c) => c.id));
  const buttons = CHECKPOINTS.map((c) => {
    const isAvailable = available.has(c.id);
    const isActive = c.id === activeId;
    const cls = !isAvailable
      ? 'text-gray-700 cursor-not-allowed'
      : isActive
        ? 'text-blue-400 border-b border-blue-400 cursor-pointer'
        : 'text-gray-500 hover:text-gray-300 cursor-pointer';
    return `<button type="button" data-checkpoint="${c.id}" ${isAvailable ? '' : 'disabled'}
              class="px-1.5 py-0.5 text-xs font-mono ${cls} transition-colors">${_esc(c.label)}</button>`;
  }).join('');
  return `<div class="payoff-checkpoint-row flex gap-1 mb-1">${buttons}</div>`;
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
    const opts = { title: group.groupName || '' };
    svgCache.set(graphId, {
      svg: buildOverlaySvg(legs, opts, 'today'),
      legs,
      opts,
      anchorId: group.groupId,
    });
  }

  for (const pos of standalone) {
    const graphId = `payoff-${encodeURIComponent(pos.symbol)}`;
    const legs = [_toLeg(pos)];
    const opts = { title: `${pos.underlying_symbol} · ${pos.expiry_date}` };
    svgCache.set(graphId, {
      svg: buildOverlaySvg(legs, opts, 'today'),
      legs,
      opts,
      anchorId: pos.symbol,
    });
  }

  function _showGraph(anchorRow, graphId) {
    if (openGraphId === graphId) { closeOpenGraph(); return; }
    closeOpenGraph();

    const cached = svgCache.get(graphId);
    if (!cached) return;

    // Checkpoint always resets to "today" on open (FR-013) — never carried
    // over from a previously opened graph's selection.
    const eligible = isEligibleForOverlay(cached.legs);
    const buttonsHtml = eligible
      ? _buildCheckpointButtonsHtml(cached.legs[0].daysToExpiry, 'today')
      : '';

    const graphRow = document.createElement('tr');
    graphRow.id = graphId;
    graphRow.className = 'payoff-graph-row';
    graphRow.dataset.checkpoint = 'today';
    graphRow.innerHTML = `<td colspan="15" class="px-4 py-3 bg-gray-900/60">${buttonsHtml}<div class="payoff-svg-container">${cached.svg}</div></td>`;
    anchorRow.insertAdjacentElement('afterend', graphRow);
    openGraphId = graphId;

    if (!eligible) return;

    // Delegated from graphRow (not the button row itself) because the button
    // row's outerHTML is replaced on every switch — a listener attached
    // directly to it would be lost after the first click.
    graphRow.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-checkpoint]');
      if (!btn || btn.disabled) return;
      const checkpointId = btn.dataset.checkpoint;
      if (checkpointId === graphRow.dataset.checkpoint) return;

      // Recompute is a cheap, direct call — no separate precomputed cache
      // needed (benchmarked at ~0.27ms worst-case for a 4-leg position,
      // well under any perceptible-delay threshold — FR-012).
      const newSvg = buildOverlaySvg(cached.legs, cached.opts, checkpointId);
      graphRow.querySelector('.payoff-svg-container').innerHTML = newSvg;
      graphRow.dataset.checkpoint = checkpointId;

      const newButtonsHtml = _buildCheckpointButtonsHtml(cached.legs[0].daysToExpiry, checkpointId);
      graphRow.querySelector('.payoff-checkpoint-row').outerHTML = newButtonsHtml;
    });
  }

  tbody.addEventListener('click', (e) => {
    // Quorum buttons open their own panel (quorum_ui.js), never the graph
    if (e.target.closest('[data-quorum-btn]')) return;

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
