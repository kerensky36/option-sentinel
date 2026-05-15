# Research: README Storage Audit

**Decision**: Update README.md in 7 locations to remove all IndexedDB references and accurately
document the sessionStorage-only storage model for trader data.

**Rationale**: The JS source files (`position_cache.js`, `screener_cache.js`, `thesis_store.js`,
`auth.js`) are the ground truth. Every stale claim in the README was verified against these files.
The constitution (v3.2.0, Principle I) explicitly prohibits IndexedDB for any trader data.

---

## Stale vs. Correct Storage Mapping

Sourced from reading the actual JS files on 2026-05-15.

| Data | README says | JS source says | Correct |
|------|-------------|----------------|---------|
| Schwab token | `sessionStorage` | `sessionStorage` (`auth.js:17`) | ✅ already correct |
| Cached positions | `IndexedDB` | `sessionStorage` (`position_cache.js:21`) | ❌ stale |
| Screener cache | (not documented) | `sessionStorage` (`screener_cache.js:8`) | ❌ missing |
| Thesis groups | `localStorage` | `localStorage` (`thesis_store.js:40`) | ✅ already correct |
| Thesis assignments | `localStorage` | `localStorage` (`thesis_store.js:56`) | ✅ already correct |
| Spread definitions | `localStorage` | not found in source | remove or verify |
| Exit goals | `localStorage` | not found in source | remove or verify |

---

## All README Locations Requiring Edits

### 1. Stack badge (top of file)
- **Current**: `stack-FastAPI%20%2B%20Vanilla%20JS%20%2B%20IndexedDB`
- **Fix**: Replace `IndexedDB` with `sessionStorage` in badge URL

### 2. Capability table ("What it does")
- **Current**: no mention of storage
- **Fix**: No change needed here

### 3. Login flow — Step 6
- **Current**: "Your browser caches position data in IndexedDB … available instantly on page reload from this cache"
- **Fix**: Replace with sessionStorage description. Note: positions do NOT survive page reload (sessionStorage is tab-scoped). Remove the "available instantly on page reload" claim — that was IndexedDB behaviour.

### 4. "Where each piece of data lives" table
- **Current rows**: token (sessionStorage ✅), cached positions (IndexedDB ❌), thesis groups (localStorage ✅), spread definitions (localStorage — verify), exit goals (localStorage — verify)
- **Fix**:
  - Change "Cached positions" row: Location → `sessionStorage`, Cleared when → "Tab/browser closed, or Erase All"
  - Add "Screener cache" row: Location → `sessionStorage`, Cleared when → "Tab/browser closed, or Erase All"
  - Remove "Spread definitions" and "Exit goals" rows if no longer in the codebase (not found in JS source)

### 5. "Erase All Data" code snippet
- **Current**:
  ```js
  sessionStorage.clear()
  localStorage.clear()
  indexedDB.deleteDatabase('option-sentinel')
  window.location.replace('/auth/login')
  ```
- **Fix**: Remove the `indexedDB.deleteDatabase(...)` line. Verify against `auth.js:66–67`.

### 6. Tech stack table
- **Current**: `Client storage | sessionStorage + IndexedDB + localStorage`
- **Fix**: `Client storage | sessionStorage + localStorage` (IndexedDB removed)

### 7. Architecture diagram (browser-side annotation)
- **Current**: `IndexedDB.put(positions)`
- **Fix**: `sessionStorage.setItem(positions)` (matches `position_cache.js:21`)

---

## Alternatives Considered

- **Leave README as-is**: Rejected. The README is the public-facing privacy guarantee. Documenting
  non-existent IndexedDB storage undermines trust and is factually wrong.
- **Add a separate "storage migration" note**: Rejected. Simpler to update the existing sections
  in place — a migration note adds noise without value.
