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
  return sessionStorage.getItem(DEMO_MODE_KEY) === 'true';
}

/**
 * Read the raw access token string from sessionStorage.
 * @returns {string|null}
 */
export function getAccessToken() {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY) || null;
}

/**
 * Check whether the user is currently authenticated.
 * @returns {boolean}
 */
export function isAuthenticated() {
  return !!getAccessToken();
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
    return demoResponse(url);
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
 * sessionStorage (all caches + token) and localStorage (thesis data) are cleared.
 * This is a failsafe — all session data already clears automatically on tab close.
 */
export function eraseAll() {
  sessionStorage.clear();
  localStorage.clear();
  window.location.replace('/auth/login');
}
