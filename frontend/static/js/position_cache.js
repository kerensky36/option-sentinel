/**
 * position_cache.js — sessionStorage-backed position cache.
 *
 * Positions are stored in sessionStorage so they survive page navigation
 * within a tab but are automatically cleared when the tab or browser closes.
 * The cache is also cleared by auth.eraseAll() on logout.
 */

const CACHE_PREFIX = 'positions';

function _key(accountHash) {
  return accountHash ? `${CACHE_PREFIX}_${accountHash}` : CACHE_PREFIX;
}

/**
 * Save a positions array to sessionStorage, keyed by account hash.
 * @param {Array<object>} positions
 * @param {string|null} accountHash
 */
export function savePositions(positions, accountHash) {
  sessionStorage.setItem(_key(accountHash), JSON.stringify({ positions, savedAt: new Date().toISOString() }));
}

/**
 * Load cached positions for the given account hash.
 * @param {string|null} accountHash
 * @returns {{positions: Array<object>, savedAt: string}|null}
 */
export function loadPositions(accountHash) {
  try {
    const raw = sessionStorage.getItem(_key(accountHash));
    if (raw === null) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Remove cached positions for the given account hash.
 * @param {string|null} accountHash
 */
export function clearPositions(accountHash) {
  sessionStorage.removeItem(_key(accountHash));
}
