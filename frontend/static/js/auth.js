/**
 * auth.js — Token management and browser storage utilities.
 *
 * The Schwab token is stored exclusively in sessionStorage under the key
 * 'schwab_token'. It is never sent to any server storage, only forwarded
 * via Authorization header on API calls.
 */

const TOKEN_KEY = 'schwab_token';
const DB_NAME = 'option-sentinel';

/**
 * Read the token dict from sessionStorage.
 * @returns {object|null} Parsed token dict, or null if not present.
 */
export function getToken() {
  try {
    const raw = sessionStorage.getItem(TOKEN_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (e) {
    console.error('auth.getToken: failed to parse token', e);
    return null;
  }
}

/**
 * Build the Authorization header value from the stored token.
 * @returns {string|null} "Bearer <base64(json)>" or null if not authenticated.
 */
export function getAuthHeader() {
  const token = getToken();
  if (!token) return null;
  try {
    const json = JSON.stringify(token);
    const b64 = btoa(unescape(encodeURIComponent(json)));
    return `Bearer ${b64}`;
  } catch (e) {
    console.error('auth.getAuthHeader: encoding failed', e);
    return null;
  }
}

/**
 * Check whether the user is currently authenticated.
 * Returns true if a token exists and its access_token_expiry is in the future.
 * @returns {boolean}
 */
export function isAuthenticated() {
  const token = getToken();
  if (!token || !token.access_token) return false;
  const expiry = token.access_token_expiry;
  if (!expiry) return true; // unknown expiry — assume valid
  const nowSeconds = Math.floor(Date.now() / 1000);
  return nowSeconds < expiry;
}

/**
 * Erase all trader data from the browser:
 *  1. sessionStorage (token)
 *  2. localStorage (thesis groups, assignments, exit goals)
 *  3. IndexedDB option-sentinel database (position cache)
 *  4. Redirect to /auth/login
 *
 * This is a client-side-only operation; no server request is made.
 */
export async function eraseAll() {
  sessionStorage.clear();
  localStorage.clear();

  try {
    await new Promise((resolve, reject) => {
      const req = indexedDB.deleteDatabase(DB_NAME);
      req.onsuccess = resolve;
      req.onerror = reject;
      req.onblocked = resolve; // proceed even if blocked
    });
  } catch (e) {
    console.warn('auth.eraseAll: IndexedDB delete failed (continuing)', e);
  }

  window.location.replace('/auth/login');
}
