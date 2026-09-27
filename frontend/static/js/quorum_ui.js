/**
 * quorum_ui.js — Macro news voting quorum panel (specs/017).
 *
 * Each option row / spread summary row carries a [data-quorum-btn] button.
 * Clicking it POSTs the row's leg symbols to /api/quorum/vote and renders the
 * verdict, tally, analyst cards, and headlines in a panel row beneath it.
 *
 * The result is held only in the DOM — never written to sessionStorage or any
 * other store (FR-015). Every string is escaped before rendering (FR-016).
 */

import { fetchWithAuth } from './auth.js';
import { getSelectedAccountHash } from './account_picker.js';

const PANEL_CLASS = 'quorum-panel-row';
const COLSPAN = 15;

const VERDICT_STYLE = {
  CLOSE: { label: 'CLOSE', cls: 'bg-red-900 text-red-200' },
  HOLD: { label: 'HOLD', cls: 'bg-gray-700 text-gray-100' },
  ROLL: { label: 'ROLL', cls: 'bg-indigo-800 text-indigo-100' },
  NO_CONSENSUS: { label: 'NO CONSENSUS', cls: 'bg-amber-900 text-amber-200' },
  NO_QUORUM: { label: 'NO QUORUM', cls: 'bg-gray-800 text-gray-300' },
};

const ACTION_BAR = { CLOSE: '#b33', HOLD: '#778', ROLL: '#56c' };

const ROLL_LABEL = { out: 'roll out', up_and_out: 'roll up & out', down_and_out: 'roll down & out' };

let _openId = null;

function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

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

/** Remove any open quorum panel. */
export function closeQuorumPanel() {
  document.querySelectorAll(`.${PANEL_CLASS}`).forEach((row) => row.remove());
  _openId = null;
}

function _panelShell(inner) {
  const row = document.createElement('tr');
  row.className = PANEL_CLASS;
  row.innerHTML = `<td colspan="${COLSPAN}" class="px-4 py-3 bg-gray-900/60">${inner}</td>`;
  return row;
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
      Convening the quorum — five analysts are reading the macro news…
    </div>${_notice()}`;
}

function _renderError(message) {
  return `<div class="text-red-400 text-sm">${esc(message)}</div>${_notice()}`;
}

function _renderTally(result) {
  return result.tally
    .map((t) => {
      const width = result.seats ? (t.votes / result.seats) * 100 : 0;
      return `
      <div class="flex items-center gap-2 text-xs">
        <span class="w-12 text-gray-300">${esc(t.action)}</span>
        <div class="flex-1 bg-gray-800" style="height:8px; border-radius:1px">
          <div style="width:${width}%; height:8px; background:${ACTION_BAR[t.action] || '#666'}; border-radius:1px"></div>
        </div>
        <span class="w-20 text-right text-gray-200">${t.votes}/${result.seats}${t.mean_confidence !== null ? ` · ${pct(t.mean_confidence)}` : ''}</span>
      </div>`;
    })
    .join('');
}

function _renderVotes(votes) {
  return votes
    .map((v) => {
      const action = v.abstained
        ? '<span class="text-gray-500">abstained</span>'
        : `<span class="font-semibold" style="color:${ACTION_BAR[v.action] || '#aaa'}">${esc(v.action)}</span>
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

function _verdictNote(result) {
  if (result.verdict === 'NO_CONSENSUS') return 'No action reached a 3-of-5 majority — status quo is to hold.';
  if (result.verdict === 'NO_QUORUM') return `Only ${result.valid_votes} of ${result.seats} analysts voted — no recommendation.`;
  const winner = result.tally.find((t) => t.action === result.verdict);
  return `${winner ? winner.votes : '?'} of ${result.seats} analysts agree.`;
}

export function renderResult(result) {
  const style = VERDICT_STYLE[result.verdict] || VERDICT_STYLE.NO_QUORUM;
  return `
    <div class="flex flex-col gap-3">
      <div class="flex flex-wrap items-center gap-3">
        <span class="px-2 py-1 text-sm font-semibold tracking-widest ${style.cls}" style="border-radius:1px">${esc(style.label)}</span>
        <span class="text-gray-300 text-sm">${esc(result.underlying_symbol)} · ${esc(_verdictNote(result))}</span>
      </div>
      <div class="flex flex-col gap-1" style="max-width:420px">${_renderTally(result)}</div>
      <div class="grid grid-cols-1 md:grid-cols-5 gap-2">${_renderVotes(result.votes)}</div>
      ${result.macro_brief ? `
      <div>
        <div class="text-gray-400 uppercase tracking-wider text-xs mb-1">Macro brief</div>
        <div class="text-gray-300 text-xs" style="line-height:1.6">${esc(result.macro_brief)}</div>
      </div>` : ''}
      <div>
        <div class="text-gray-400 uppercase tracking-wider text-xs mb-1">Headlines used</div>
        ${_renderHeadlines(result.headlines)}
      </div>
      <div class="text-gray-500 text-xs">${esc(result.disclaimer)} · ${esc(result.model)}</div>
    </div>${_notice()}`;
}

function _errorMessage(status) {
  switch (status) {
    case 404: return 'This position is no longer in the account — refresh positions and try again.';
    case 429: return 'Too many quorum requests — try again in a minute.';
    case 503: return 'Quorum is not configured on this server.';
    case 504: return 'The quorum timed out — try again.';
    default: return `Quorum failed (HTTP ${status}).`;
  }
}

async function _openPanel(anchorRow, id, symbols) {
  if (_openId === id) { closeQuorumPanel(); return; }
  closeQuorumPanel();

  const panel = _panelShell(_renderLoading());
  anchorRow.insertAdjacentElement('afterend', panel);
  _openId = id;
  const cell = panel.firstElementChild;

  try {
    const resp = await fetchWithAuth('/api/quorum/vote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbols, account_hash: getSelectedAccountHash() || null }),
    });
    if (!resp) return; // 401 already handled by fetchWithAuth
    if (_openId !== id) return; // closed or replaced while waiting
    if (!resp.ok) {
      cell.innerHTML = _renderError(_errorMessage(resp.status));
      return;
    }
    cell.innerHTML = renderResult(await resp.json());
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

  const symbolsById = new Map();
  for (const g of groups) symbolsById.set(g.groupId, g.legs.map((l) => l.symbol));
  for (const p of standalone) symbolsById.set(p.symbol, [p.symbol]);

  const tbody = container.querySelector('tbody');
  if (!tbody) return;

  tbody.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-quorum-btn]');
    if (!btn) return;
    e.stopPropagation();
    const id = btn.getAttribute('data-quorum-btn');
    const symbols = symbolsById.get(id);
    const anchorRow = btn.closest('tr');
    if (!symbols || !anchorRow) return;
    _openPanel(anchorRow, id, symbols);
  });
}

/**
 * HTML for a row's quorum button cell.
 * @param {string} id - groupId for spreads, symbol for standalone legs
 */
export function quorumButtonCell(id) {
  return `<td class="px-2 py-1 text-right">
      <button data-quorum-btn="${esc(id)}" title="Ask the macro news quorum: close, hold, or roll?"
        class="bg-gray-800 hover:bg-gray-700 text-gray-300 px-2 py-0.5 uppercase tracking-wider text-xs">Quorum</button>
    </td>`;
}
