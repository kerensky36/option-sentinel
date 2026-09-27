/**
 * quorum_cache.js — Session cache of quorum results (specs/020 FR-324, D-314).
 *
 * The first successful result for a position (row id + its sorted leg symbols)
 * is kept in sessionStorage with its summary outcome, so later clicks show it
 * without a new request. sessionStorage is cleared by sign-out, Erase All Data
 * and tab close (constitution Principle I), which is exactly the lifetime the
 * user asked for. Nothing here is ever sent anywhere.
 *
 * When sessionStorage throws (private mode, quota), an in-memory Map keeps
 * results for the page's lifetime instead.
 */

const PREFIX = 'quorum:v1:';
const _memory = new Map();

/**
 * Storage key for a position: row id plus sorted leg symbols, so a rolled or
 * partly closed spread gets a fresh quorum while price moves alone do not.
 * @param {string} id - groupId for spreads, symbol for standalone options
 * @param {Array<{symbol: string}>} legs
 */
export function cacheKey(id, legs) {
  const symbols = (legs || []).map((l) => String(l.symbol ?? '')).sort();
  return `${PREFIX}${id}|${symbols.join(',')}`;
}

/** Saved entry for a key, or null. */
export function load(key) {
  try {
    const raw = globalThis.sessionStorage?.getItem(key);
    if (raw) return JSON.parse(raw);
  } catch {
    // storage blocked or corrupt entry → fall back to memory
  }
  return _memory.has(key) ? _memory.get(key) : null;
}

/** Save an entry ({result, summary}) for the rest of the session. */
export function save(key, entry) {
  _memory.set(key, entry);
  try {
    globalThis.sessionStorage?.setItem(key, JSON.stringify(entry));
  } catch {
    // quota exceeded or storage blocked → the in-memory copy still serves this page
  }
}
