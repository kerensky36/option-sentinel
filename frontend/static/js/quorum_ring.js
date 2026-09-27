/**
 * quorum_ring.js — Radial vote ring for the advice panel (specs/020 FR-304, FR-305, D-309).
 *
 * Pure ES module: no DOM access. ringSvg() returns an SVG string with one wedge
 * per seat in fixed order. Wedge fill length is the analyst's confidence, the
 * outer band is the vote colour, and every wedge carries a text label so the
 * vote never depends on colour alone (SC-307). CLOSE fills are hatched.
 */

/** Vote colours. Deliberately not the app's P&L green/red or warning yellow. */
export const VOTE_COLORS = { CLOSE: '#e8703a', HOLD: '#8c93a8', ROLL: '#3aa8e0', NONE: '#3a3a4a' };

/** Tinted verdict badge colours (background, text). */
export const VERDICT_BADGE = {
  CLOSE: { label: 'CLOSE', bg: '#3a1c0c', fg: '#f59a6a' },
  HOLD: { label: 'HOLD', bg: '#252836', fg: '#c4cadb' },
  ROLL: { label: 'ROLL', bg: '#0c2434', fg: '#7cc8f0' },
  NO_CONSENSUS: { label: 'NO CONSENSUS', bg: '#1c1c24', fg: '#aeaeb8' },
  NO_QUORUM: { label: 'NO QUORUM', bg: '#1c1c24', fg: '#90909c' },
};

export const ROLL_LABEL = { out: 'out', up_and_out: 'up & out', down_and_out: 'down & out' };

const SHORT = {
  greeks_exposure: 'GREEKS',
  volatility_pricing: 'VOL',
  time_decay_pnl: 'DECAY',
  strike_assignment: 'STRIKE',
  macro_news_overlay: 'MACRO',
};

const CX = 140;
const CY = 140;
const R_IN = 50;
const R_OUT = 104;
const GAP = 3;
const LABEL_R = 128;

export function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** The roll direction every ROLL voter shares, or null when they differ or none rolled. */
export function sharedRollDirection(votes) {
  const dirs = new Set(votes.filter((v) => !v.abstained && v.action === 'ROLL').map((v) => v.roll_direction));
  return dirs.size === 1 ? [...dirs][0] : null;
}

/** Verdict badge text, e.g. "ROLL OUT" when all ROLL voters agree on a direction. */
export function verdictLabel(result) {
  const base = (VERDICT_BADGE[result.verdict] || VERDICT_BADGE.NO_QUORUM).label;
  if (result.verdict !== 'ROLL') return base;
  const dir = sharedRollDirection(result.votes || []);
  return dir ? `ROLL ${ROLL_LABEL[dir].toUpperCase()}` : 'ROLL';
}

function polar(r, deg) {
  const a = ((deg - 90) * Math.PI) / 180;
  return [CX + r * Math.cos(a), CY + r * Math.sin(a)];
}

function arc(r0, r1, a0, a1) {
  const f = (n) => n.toFixed(2);
  const [x0, y0] = polar(r1, a0);
  const [x1, y1] = polar(r1, a1);
  const [x2, y2] = polar(r0, a1);
  const [x3, y3] = polar(r0, a0);
  return `M${f(x0)},${f(y0)} A${f(r1)},${f(r1)} 0 0 1 ${f(x1)},${f(y1)} L${f(x2)},${f(y2)} A${r0},${r0} 0 0 0 ${f(x3)},${f(y3)}Z`;
}

function voteText(v) {
  if (v.abstained || !v.action) return 'ABSTAIN';
  return v.action === 'ROLL' && v.roll_direction ? `ROLL ${ROLL_LABEL[v.roll_direction] || v.roll_direction}` : v.action;
}

function pct(c) {
  return `${Math.round(Number(c) * 100)}%`;
}

function centreLines(result) {
  const valid = result.votes.filter((v) => !v.abstained && v.action).length;
  const seats = result.seats || result.votes.length;
  if (result.verdict === 'NO_CONSENSUS') return ['NO', 'CONSENSUS', `${valid} of ${seats} voted`];
  if (result.verdict === 'NO_QUORUM') return ['NO', 'QUORUM', `${valid} of ${seats} voted`];
  const winner = result.votes.filter((v) => !v.abstained && v.action === result.verdict).length;
  const dir = result.verdict === 'ROLL' ? sharedRollDirection(result.votes) : null;
  const mid = dir ? ROLL_LABEL[dir].toUpperCase() : null;
  return [result.verdict, mid, `${winner} of ${seats}`];
}

/**
 * Build the vote ring SVG.
 * @param {object} result - QuorumResult (votes in seat order)
 * @param {{animate?: boolean}} [opts]
 * @returns {string}
 */
export function ringSvg(result, { animate = false } = {}) {
  const votes = result.votes || [];
  const seg = 360 / Math.max(votes.length, 1);
  const half = R_IN + (R_OUT - R_IN) * 0.5;
  let body = `
    <circle cx="${CX}" cy="${CY}" r="${half}" fill="none" stroke="#2c2c3a" stroke-dasharray="2,3"/>
    <circle cx="${CX}" cy="${CY}" r="${R_OUT}" fill="none" stroke="#2c2c3a"/>`;

  votes.forEach((v, i) => {
    const a0 = i * seg - seg / 2 + GAP / 2;
    const a1 = (i + 1) * seg - seg / 2 - GAP / 2;
    const abstained = v.abstained || !v.action;
    const key = abstained ? 'NONE' : v.action;
    const colour = VOTE_COLORS[key];
    const rFill = abstained ? R_IN + 4 : R_IN + (R_OUT - R_IN) * Math.max(0, Math.min(1, Number(v.confidence) || 0));
    const fill = key === 'CLOSE' ? 'url(#hatch)' : colour;
    const [lx, ly] = polar(LABEL_R, (a0 + a1) / 2);
    const anchor = Math.abs(lx - CX) < 8 ? 'middle' : lx > CX ? 'start' : 'end';
    const text = voteText(v);
    const aria = abstained
      ? `${v.lens}: abstained`
      : `${v.lens}: ${text}, ${pct(v.confidence)} confidence`;
    const delay = animate ? ` style="animation-delay:${(i * 0.2 + 0.1).toFixed(1)}s"` : '';
    body += `
    <g class="wedge" data-seat="${esc(v.seat)}" tabindex="0" role="button" aria-label="${esc(aria)}">
      <path class="wedge-track" d="${arc(R_IN, R_OUT, a0, a1)}" fill="#1c1c24" stroke="#22222e"/>
      <path class="wedge-fill${animate ? ' anim' : ''}"${delay} d="${arc(R_IN, rFill, a0, a1)}" fill="${fill}" fill-opacity="${abstained ? 0.6 : 0.9}"/>
      <path class="wedge-band" d="${arc(R_OUT + 3, R_OUT + 7, a0, a1)}" fill="${colour}"/>
      <text x="${lx.toFixed(1)}" y="${(ly - 4).toFixed(1)}" text-anchor="${anchor}" font-size="11" font-weight="600" letter-spacing="1" fill="#c6c6cc">${esc(SHORT[v.seat] || v.seat)}</text>
      <text x="${lx.toFixed(1)}" y="${(ly + 10).toFixed(1)}" text-anchor="${anchor}" font-size="10" fill="${abstained ? '#626270' : colour}">${esc(text)}${abstained ? '' : ` ${pct(v.confidence)}`}</text>
    </g>`;
  });

  const badge = VERDICT_BADGE[result.verdict] || VERDICT_BADGE.NO_QUORUM;
  const [top, mid, sub] = centreLines(result);
  const big = (mid && mid.length > 6) ? 11 : 15;
  body += `
    <circle cx="${CX}" cy="${CY}" r="${R_IN - 4}" fill="#14141a" stroke="#2c2c3a"/>
    <text class="centre" x="${CX}" y="${mid ? CY - 8 : CY}" text-anchor="middle" font-size="${big}" font-weight="700" letter-spacing="2" fill="${badge.fg}">${esc(top)}</text>
    ${mid ? `<text class="centre" x="${CX}" y="${CY + 6}" text-anchor="middle" font-size="${mid.length > 6 ? 9 : 13}" font-weight="700" letter-spacing="1" fill="${badge.fg}">${esc(mid)}</text>` : ''}
    <text class="centre centre-sub" x="${CX}" y="${CY + 22}" text-anchor="middle" font-size="10" fill="#90909c">${esc(sub)}</text>`;

  return `<svg class="vote-ring" viewBox="-90 0 460 280" font-family="JetBrains Mono, monospace" role="img" aria-label="Vote ring">
    <defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="${VOTE_COLORS.CLOSE}"/><rect width="2" height="6" fill="#14141a" fill-opacity="0.55"/></pattern></defs>${body}
  </svg>`;
}
