const CACHE_PREFIX = 'screener_results';

function _key(accountHash) {
  return accountHash ? `${CACHE_PREFIX}_${accountHash}` : CACHE_PREFIX;
}

export function saveScreenerResults(results, accountHash) {
  sessionStorage.setItem(_key(accountHash), JSON.stringify(results));
}

export function loadScreenerResults(accountHash) {
  try {
    const raw = sessionStorage.getItem(_key(accountHash));
    if (raw === null) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearScreenerResults(accountHash) {
  sessionStorage.removeItem(_key(accountHash));
}
