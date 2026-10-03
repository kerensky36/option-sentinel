/**
 * auth_handoff.js — the /auth hand-off pages (callback, demo-login, dev-login,
 * logout), moved out of inline scripts for the strict CSP (specs/023): Firebase
 * adds a nonce-free script-src to the /auth/** pages it proxies to Cloud Run.
 * The page names its job in <body data-handoff> ("live" also carries data-token).
 */
(async function () {
  const { handoff, token } = document.body.dataset;

  if (handoff === 'logout') {
    sessionStorage.clear();
    localStorage.clear();
    try {
      await new Promise((resolve, reject) => {
        const req = indexedDB.deleteDatabase('option-sentinel');
        req.onsuccess = resolve;
        req.onerror = reject;
        req.onblocked = resolve;
      });
    } catch (e) {
      console.warn('IndexedDB clear failed:', e);
    }
    window.location.replace('/auth/login');
    return;
  }

  try {
    if (handoff === 'demo') {
      sessionStorage.setItem('demo_mode', 'true');
    } else if (handoff === 'live') {
      sessionStorage.removeItem('demo_mode');
      sessionStorage.setItem('schwab_access_token', token);
    }
  } catch (e) {
    console.error('Failed to store session state:', e);
  }
  window.location.replace('/');
})();
