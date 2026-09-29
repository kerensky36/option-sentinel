/**
 * auth.js — Token management and browser storage utilities.
 *
 * The Schwab access token is stored exclusively in sessionStorage under the key
 * 'schwab_access_token'. It is never sent to any server storage, only forwarded
 * via Authorization header on API calls. Any 401 response triggers eraseAll()
 * and redirects to login — there is no silent token refresh.
 */

const ACCESS_TOKEN_KEY = 'schwab_access_token';
const DEMO_MODE_KEY = 'demo_mode';

/**
 * Returns true when the current tab is running in demo mode.
 * @returns {boolean}
 */
export function isDemoMode() {
  try {
    return globalThis.sessionStorage?.getItem(DEMO_MODE_KEY) === 'true';
  } catch {
    return false; // storage blocked
  }
}

/**
 * sessionStorage key for the current mode (specs/021 FR-406). Demo keys carry a
 * `demo:` prefix so demo and live state never overwrite or leak into each other;
 * live keys keep their original names.
 * @param {string} key
 * @returns {string}
 */
export function scopedKey(key) {
  return isDemoMode() ? `demo:${key}` : key;
}

/**
 * True when a Schwab access token is stored (it is kept while demo mode is on).
 * @returns {boolean}
 */
export function hasLiveToken() {
  return !!getAccessToken();
}

/**
 * Switch between demo and live mode, keeping each mode's saved state
 * (specs/021 FR-402–FR-404). Reloads the current page in the new mode; going
 * live with no stored token starts the Schwab OAuth flow instead.
 * @param {'demo'|'live'} target
 * @param {Location} [loc]
 */
export function switchMode(target, loc = window.location) {
  if (target === 'demo') {
    sessionStorage.setItem(DEMO_MODE_KEY, 'true');
    loc.reload();
  } else if (hasLiveToken()) {
    sessionStorage.removeItem(DEMO_MODE_KEY);
    loc.reload();
  } else {
    loc.assign('/auth/start');
  }
}

/**
 * Read the raw access token string from sessionStorage.
 * @returns {string|null}
 */
export function getAccessToken() {
  return globalThis.sessionStorage?.getItem(ACCESS_TOKEN_KEY) || null;
}

/**
 * Check whether the user is currently authenticated (real token or demo mode).
 * @returns {boolean}
 */
export function isAuthenticated() {
  return isDemoMode() || !!getAccessToken();
}

/**
 * Fetch a URL with the Bearer Authorization header attached.
 * On 401: calls eraseAll() (clears all storage and redirects to login).
 * Returns null if not authenticated or after a 401.
 *
 * @param {string} url
 * @param {RequestInit} [options]
 * @returns {Promise<Response|null>}
 */
export async function fetchWithAuth(url, options = {}) {
  if (isDemoMode()) {
    const { demoResponse } = await import('./demo_data.js');
    return demoResponse(url, options);
  }

  const token = getAccessToken();
  if (!token) {
    eraseAll();
    return null;
  }

  const resp = await fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });

  if (resp.status === 401) {
    eraseAll();
    return null;
  }

  return resp;
}

/**
 * Erase all trader data from the browser and redirect to login.
 * sessionStorage (all caches + token) and localStorage are cleared.
 * This is a failsafe — all session data already clears automatically on tab close.
 */
export function eraseAll() {
  sessionStorage.clear();
  localStorage.clear();
  window.location.replace('/auth/login');
}
