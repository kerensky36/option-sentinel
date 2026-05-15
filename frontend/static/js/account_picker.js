/**
 * account_picker.js — Schwab account picker for the top navigation bar.
 *
 * Fetches all accounts for the current token, populates #account-picker,
 * and provides helpers for appending the selected account hash to API URLs.
 *
 * US1: picker visible, account_hash sent on API calls
 * US2: sessionStorage persistence across page nav and refresh
 * US3: single-account auto-select, non-interactive
 */

import { fetchWithAuth } from './auth.js';

const ACCOUNT_HASH_KEY = 'schwab_selected_account';
const PICKER_ID = 'account-picker';

let _selectedHash = null;

/**
 * Returns the currently selected account hash from module state, or null.
 * @returns {string|null}
 */
export function getSelectedAccountHash() {
  return _selectedHash;
}

/**
 * Appends ?account_hash=<hash> to a URL if a selection exists.
 * @param {string} url
 * @returns {string}
 */
export function withAccountHash(url) {
  if (!_selectedHash) return url;
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}account_hash=${encodeURIComponent(_selectedHash)}`;
}

function _setSelection(hash) {
  _selectedHash = hash;
  sessionStorage.setItem(ACCOUNT_HASH_KEY, hash);
  document.dispatchEvent(new CustomEvent('accountchange', { detail: { accountHash: hash } }));
}

async function init() {
  const select = document.getElementById(PICKER_ID);
  if (!select) return;

  const resp = await fetchWithAuth('/api/accounts');
  if (!resp) return; // 401 — eraseAll() already called by fetchWithAuth

  if (!resp.ok) {
    select.innerHTML = '<option value="" disabled selected>Error loading accounts</option>';
    select.disabled = true;
    select.style.opacity = '0.4';
    return;
  }

  const accounts = await resp.json();

  if (accounts.length === 0) {
    select.innerHTML = '<option value="" disabled selected>No accounts</option>';
    select.disabled = true;
    select.style.opacity = '0.4';
    return;
  }

  // Restore stored selection; discard stale hash (FR-008)
  const stored = sessionStorage.getItem(ACCOUNT_HASH_KEY);
  const validHashes = new Set(accounts.map(a => a.hashValue));
  const initialHash = (stored && validHashes.has(stored)) ? stored : accounts[0].hashValue;

  select.innerHTML = accounts
    .map(a => `<option value="${a.hashValue}"${a.hashValue === initialHash ? ' selected' : ''}>${a.accountNumber}</option>`)
    .join('');

  _setSelection(initialHash);

  // US3: single account — non-interactive
  if (accounts.length === 1) {
    select.disabled = true;
    select.title = 'Only one account on this token';
  } else {
    select.addEventListener('change', () => _setSelection(select.value));
  }
}

init();
