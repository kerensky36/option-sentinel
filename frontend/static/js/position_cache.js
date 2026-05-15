/**
 * position_cache.js — IndexedDB-backed position cache.
 *
 * Positions are stored in IndexedDB so they survive page refreshes within a
 * session. The cache is cleared by auth.eraseAll() on logout.
 */

const DB_NAME = 'option-sentinel';
const DB_VERSION = 1;
const STORE_NAME = 'positions';
const CACHE_KEY = 'latest';

/**
 * Open (or create) the IndexedDB database.
 * @returns {Promise<IDBDatabase>}
 */
function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Save a positions array to IndexedDB under key 'latest'.
 * @param {Array<object>} positions - Array of PositionView objects.
 * @returns {Promise<void>}
 */
export async function savePositions(positions) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const req = store.put({ positions, savedAt: new Date().toISOString() }, CACHE_KEY);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
    tx.oncomplete = () => db.close();
  });
}

/**
 * Load the latest cached positions from IndexedDB.
 * @returns {Promise<{positions: Array<object>, savedAt: string}|null>}
 */
export async function loadPositions() {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(CACHE_KEY);
      req.onsuccess = () => {
        db.close();
        resolve(req.result || null);
      };
      req.onerror = () => {
        db.close();
        reject(req.error);
      };
    });
  } catch (e) {
    console.warn('position_cache.loadPositions: failed', e);
    return null;
  }
}

/**
 * Delete all records from the positions store.
 * @returns {Promise<void>}
 */
export async function clearPositions() {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const req = store.clear();
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
      tx.oncomplete = () => db.close();
    });
  } catch (e) {
    console.warn('position_cache.clearPositions: failed', e);
  }
}
