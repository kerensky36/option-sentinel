/**
 * quorum_ui.js — Advice panel for the voting quorum (specs/017, 018, 020).
 *
 * Each standalone option row and spread summary row carries an ADVICE(Agentic)
 * button next to its name (specs/020 FR-301). Clicking it POSTs the row's legs
 * — as held from the last positions refresh, with their realised volatility and
 * "as of" time — to /api/quorum/vote (specs/018 FR-110) and renders the verdict,
 * the radial vote ring and the analysts beneath that row. No account identifier
 * is sent.
 *
 * The result is held only in the DOM — never written to sessionStorage or any
 * other store (FR-015). Every string is escaped before rendering (FR-016).
 */

import { fetchWithAuth } from './auth.js';
import { VERDICT_BADGE, VOTE_COLORS, esc, ringSvg, verdictLabel } from './quorum_ring.js';

const PANEL_CLASS = 'quorum-panel-row';
const COLSPAN = 14;
const WARNING_NOTE_ID = 'advice-warning-note';

const ROLL_LABEL = { out: 'roll out', up_and_out: 'roll up & out', down_and_out: 'roll down & out' };

const WARNING_TEXT = 'AI-generated opinion. Not financial advice. Option Sentinel never places trades.';

const STALE_MESSAGE = 'Position data is more than 15 minutes old — refresh positions and try again.';

// Leg fields the quorum endpoint accepts (QuorumLegIn); anything else is rejected.
const LEG_FIELDS = [
  'underlying_symbol', 'option_type', 'strike', 'expiry_date', 'days_to_expiry',
  'quantity', 'cost', 'current_mark', 'unrealised_pnl', 'delta', 'gamma', 'theta',
  'vega', 'implied_volatility', 'underlying_price',
];

let _openId = null;
let _openBtn = null;

function safeLink(url) {
  try {
    const u = new URL(url);
    return u.protocol === 'https:' || u.protocol === 'http:' ? u.href : null;
  } catch {
    return null;
  }
}

function pct(x) {
  return x === null || x === undefined ? '—' : `${Math.round(Number(x) * 100)}%`;
}

/** Remove any open quorum panel. Only quorum panel rows are touched — never the payoff graph. */
export function closeQuorumPanel(root = globalThis.document) {
  if (root) root.querySelectorAll(`.${PANEL_CLASS}`).forEach((row) => row.remove());
  if (_openBtn) _openBtn.setAttribute('aria-expanded', 'false');
  _openBtn = null;
  _openId = null;
}

function _panelShell(inner) {
  const row = document.createElement('tr');
  row.className = PANEL_CLASS;
  row.innerHTML = `<td colspan="${COLSPAN}" class="quorum-panel-cell"><div class="quorum-panel-inner">${inner}</div></td>`;
  return row;
}

// Keep the panel as wide as the visible table area so it never scrolls
// sideways with a wide table on a phone (FR-319, D-310).
function _fitPanel() {
  const inner = document.querySelector(`.${PANEL_CLASS} .quorum-panel-inner`);
  const scroller = inner?.closest('.overflow-x-auto');
  if (inner && scroller) inner.style.width = `${scroller.clientWidth}px`;
}

let _resizeWired = false;
function _wireResize() {
  if (_resizeWired || typeof window === 'undefined') return;
  window.addEventListener('resize', _fitPanel);
  _resizeWired = true;
}

// Wedge ↔ analyst-row linking (FR-304, FR-320).
function _wireRing(root) {
  const highlight = (seat, on) => {
    root.querySelectorAll(`[data-seat="${CSS.escape(seat)}"]`).forEach((el) => el.classList.toggle('hl', on));
  };
  const openRow = (seat) => {
    const row = root.querySelector(`details.member[data-seat="${CSS.escape(seat)}"]`);
    if (!row) return;
    row.open = true;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    row.scrollIntoView({ block: 'nearest', behavior: reduce ? 'auto' : 'smooth' });
  };
  root.querySelectorAll('.wedge[data-seat]').forEach((w) => {
    const seat = w.getAttribute('data-seat');
    w.addEventListener('mouseenter', () => highlight(seat, true));
    w.addEventListener('mouseleave', () => highlight(seat, false));
    w.addEventListener('focus', () => highlight(seat, true));
    w.addEventListener('blur', () => highlight(seat, false));
    w.addEventListener('click', () => openRow(seat));
    w.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openRow(seat); }
    });
  });
  root.querySelectorAll('details.member[data-seat]').forEach((d) => {
    const seat = d.getAttribute('data-seat');
    d.addEventListener('mouseenter', () => highlight(seat, true));
    d.addEventListener('mouseleave', () => highlight(seat, false));
  });
}

function _notice() {
  return `
    <p class="text-gray-400 text-xs mt-3">
      Position and market data (no identifying information) is sent to Google Vertex AI.
      <a href="/data-use" class="underline text-gray-300">How we use your data</a>
    </p>`;
}

function _renderLoading() {
  return `
    <div class="text-gray-300 text-sm flex items-center gap-2">
      <span class="animate-pulse">●</span>
      Convening the quorum — five analysts are reviewing the position…
    </div>${_notice()}`;
}

function _renderError(message) {
  return `<div class="text-red-400 text-sm">${esc(message)}</div>${_notice()}`;
}

function _renderTally(result) {
  const counts = { CLOSE: 0, HOLD: 0, ROLL: 0 };
  let abstain = 0;
  for (const v of result.votes) {
    if (v.abstained || !v.action) abstain += 1;
    else counts[v.action] += 1;
  }
  const item = (key, n) => `<span${result.verdict === key ? ' class="win"' : ''}><i class="sw" style="background:${VOTE_COLORS[key]}"></i>${key} ${n}</span>`;
  const parts = Object.keys(counts).map((k) => item(k, counts[k]));
  if (abstain) parts.push(`<span><i class="sw" style="background:${VOTE_COLORS.NONE}"></i>ABSTAIN ${abstain}</span>`);
  return parts.join('');
}

function _renderVotes(votes) {
  return votes
    .map((v) => {
      const action = v.abstained
        ? '<span class="text-gray-500">abstained</span>'
        : `<span class="font-semibold" style="color:${VOTE_COLORS[v.action] || '#aaa'}">${esc(v.action)}</span>
           <span class="text-gray-400">${pct(v.confidence)}</span>
           ${v.roll_direction ? `<span class="text-gray-300">· ${esc(ROLL_LABEL[v.roll_direction] || v.roll_direction)}</span>` : ''}`;
      return `
      <div class="border border-gray-800 bg-gray-900 px-3 py-2" style="border-radius:2px">
        <div class="text-gray-400 uppercase tracking-wider text-xs mb-1">${esc(v.lens)}</div>
        <div class="text-sm mb-1">${action}</div>
        <div class="text-gray-300 text-xs" style="line-height:1.5">${esc(v.rationale)}</div>
      </div>`;
    })
    .join('');
}

function _renderHeadlines(headlines) {
  if (!headlines || headlines.length === 0) {
    return '<div class="text-gray-500 text-xs">No headlines could be retrieved.</div>';
  }
  return `<ul class="space-y-1" style="list-style:none; padding:0">${headlines
    .map((h) => {
      const href = safeLink(h.link);
      const title = href
        ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer" class="text-gray-200 underline">${esc(h.title)}</a>`
        : `<span class="text-gray-200">${esc(h.title)}</span>`;
      return `<li class="text-xs"><span class="text-gray-400">${esc(h.publisher)}</span> · ${title}</li>`;
    })
    .join('')}</ul>`;
}

function _asOfLabel(asOf) {
  const d = new Date(asOf);
  if (Number.isNaN(d.getTime())) return '';
  return `Data as of ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

function _verdictNote(result) {
  if (result.verdict === 'NO_CONSENSUS') return 'No action reached a 3-of-5 majority — status quo is to hold.';
  if (result.verdict === 'NO_QUORUM') return `Only ${result.valid_votes} of ${result.seats} analysts voted — no recommendation.`;
  const winner = result.tally.find((t) => t.action === result.verdict);
  return `${winner ? winner.votes : '?'} of ${result.seats} analysts agree.`;
}

export function renderResult(result) {
  const badge = VERDICT_BADGE[result.verdict] || VERDICT_BADGE.NO_QUORUM;
  return `
    <div class="quorum-panel">
      <div class="result-head">
        <span class="verdict" style="background:${badge.bg};color:${badge.fg}">${esc(verdictLabel(result))}</span>
        <span class="verdict-note">${esc(result.underlying_symbol)} · ${esc(_verdictNote(result))}</span>
        ${result.as_of ? `<span class="asof">${esc(_asOfLabel(result.as_of))}</span>` : ''}
      </div>
      <div class="warn-strip" role="note"><span aria-hidden="true">⚠</span> ${esc(WARNING_TEXT)}</div>
      <div class="overview">
        <div class="radial-card">
          ${ringSvg(result)}
          <div class="tally">${_renderTally(result)}</div>
          <div class="radial-note">Wedge length = the analyst's confidence. Outer band = their vote. Three matching votes make a majority.</div>
        </div>
        <div class="summary-area" data-state="none"></div>
      </div>
      <div class="members grid grid-cols-1 md:grid-cols-5 gap-2">${_renderVotes(result.votes)}</div>
      ${result.macro_brief ? `
      <div>
        <div class="text-gray-400 uppercase tracking-wider text-xs mb-1">Research brief (Macro &amp; News analyst)</div>
        <div class="text-gray-300 text-xs" style="line-height:1.6">${esc(result.macro_brief)}</div>
      </div>` : ''}
      <div>
        <div class="text-gray-400 uppercase tracking-wider text-xs mb-1">News given to the Macro &amp; News analyst</div>
        ${_renderHeadlines(result.headlines)}
      </div>
      <div class="foot">${esc(result.disclaimer)} · ${esc(result.model)}</div>
    </div>${_notice()}`;
}

function _errorMessage(status) {
  switch (status) {
    case 409: return STALE_MESSAGE;
    case 422: return 'Quorum request was rejected — refresh positions and try again.';
    case 502: return 'Could not verify your Schwab login — try again.';
    case 429: return 'Too many quorum requests — try again in a minute.';
    case 503: return 'Quorum is not configured on this server.';
    case 504: return 'The quorum timed out — try again.';
    default: return `Quorum failed (HTTP ${status}).`;
  }
}

/**
 * Build the v2 request body from full position objects, or null if any leg
 * has no "as of" time (cached before this feature — treat as stale).
 * @param {Array<object>} legs
 */
export function buildQuorumRequest(legs) {
  if (!legs.length || legs.some((l) => !l.as_of)) return null;
  const asOf = legs.map((l) => l.as_of).sort((a, b) => new Date(a) - new Date(b))[0];
  return {
    as_of: asOf,
    legs: legs.map((l) => {
      const out = {};
      for (const key of LEG_FIELDS) out[key] = l[key] ?? null;
      out.realised_volatility = l.fundamentals?.realised_volatility ?? null;
      return out;
    }),
  };
}

async function _openPanel(anchorRow, id, legs, btn) {
  if (_openId === id) { closeQuorumPanel(); return; }
  closeQuorumPanel();
  _openBtn = btn || null;
  if (_openBtn) _openBtn.setAttribute('aria-expanded', 'true');

  const panel = _panelShell(_renderLoading());
  anchorRow.insertAdjacentElement('afterend', panel);
  _openId = id;
  const cell = panel.querySelector('.quorum-panel-inner');
  _wireResize();
  _fitPanel();

  const body = buildQuorumRequest(legs);
  if (!body) {
    cell.innerHTML = _renderError(STALE_MESSAGE);
    return;
  }

  try {
    const resp = await fetchWithAuth('/api/quorum/vote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp) return; // 401 already handled by fetchWithAuth
    if (_openId !== id) return; // closed or replaced while waiting
    if (!resp.ok) {
      cell.innerHTML = _renderError(_errorMessage(resp.status));
      return;
    }
    const result = await resp.json();
    cell.innerHTML = renderResult(result);
    _wireRing(cell);
  } catch (err) {
    console.error('quorum_ui: request failed', err);
    if (_openId === id) cell.innerHTML = _renderError('Quorum request failed — check your connection and try again.');
  }
}

/**
 * Wire quorum buttons inside the positions table.
 * @param {HTMLElement} container - element holding the positions <table>
 * @param {{groups: Array<object>, standalone: Array<object>}} positionData
 */
export function initQuorum(container, positionData) {
  const { groups = [], standalone = [] } = positionData || {};
  closeQuorumPanel();

  const legsById = new Map();
  for (const g of groups) legsById.set(g.groupId, g.legs);
  for (const p of standalone) legsById.set(p.symbol, [p]);

  const tbody = container.querySelector('tbody');
  if (!tbody) return;

  if (!document.getElementById(WARNING_NOTE_ID)) {
    container.insertAdjacentHTML('beforeend', adviceWarningNote());
  }

  tbody.addEventListener('click', (e) => {
    onTableClick(e, (id, btn) => {
      const legs = legsById.get(id);
      const anchorRow = btn.closest('tr');
      if (!legs || !anchorRow) return;
      _openPanel(anchorRow, id, legs, btn);
    });
  });
}

/**
 * Handle a click inside the positions table body. Returns true when it was an
 * ADVICE(Agentic) button: the event is stopped so the spread toggle and the
 * payoff graph never react to it (FR-303).
 * @param {Event} e
 * @param {(id: string, btn: Element) => void} open
 */
export function onTableClick(e, open) {
  const btn = e.target.closest('[data-quorum-btn]');
  if (!btn) return false;
  e.stopPropagation();
  if (typeof open === 'function') open(btn.getAttribute('data-quorum-btn'), btn);
  return true;
}

/**
 * The ADVICE(Agentic) button placed after a position's name (FR-301, FR-302).
 * The hazard stripe is its warning label; the shared note gives screen readers
 * the same warning.
 * @param {string} id - groupId for spreads, symbol for standalone legs
 */
export function adviceButton(id) {
  return `<button type="button" class="advice-btn" data-quorum-btn="${esc(id)}" aria-expanded="false"
      aria-describedby="${WARNING_NOTE_ID}" title="Five AI analysts vote close, hold or roll. AI opinion, not financial advice."><span class="hazard" aria-hidden="true"></span><span class="advice-label">ADVICE(Agentic)</span></button>`;
}

/** Visually hidden description shared by every ADVICE(Agentic) button. */
export function adviceWarningNote() {
  return `<span id="${WARNING_NOTE_ID}" class="sr-only">AI opinion. Not financial advice. Option Sentinel never places trades.</span>`;
}
