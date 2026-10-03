# Implementation Plan: Seamless, Stateful Demo ↔ Live Mode Switch

**Branch**: `021-seamless-mode-switch` | **Spec**: [spec.md](./spec.md)

## Summary

Scope every client cache key by mode (live keys unchanged, demo keys prefixed
`demo:`), add `switchMode()` to `auth.js`, add a DEMO | LIVE switch to the nav
in `base.html`, and make the token-storing auth pages clear the demo flag.

## Technical Context

Vanilla ES modules in `frontend/static/js`, Jinja templates, FastAPI auth
router. Tests: pytest, with a Node harness for pure JS modules (same pattern as
`tests/unit/quorum_ui_harness.mjs`).

## Design

- `auth.js`
  - `scopedKey(key)` → `demo:${key}` in demo mode, `key` otherwise.
  - `hasLiveToken()` → a Schwab token is stored.
  - `switchMode(target, loc = window.location)` → `'demo'`: set flag, `loc.reload()`;
    `'live'` with token: remove flag, `loc.reload()`; `'live'` without token: `loc.assign('/auth/start')`.
  - `isDemoMode()` reads `globalThis.sessionStorage?.` so modules import cleanly in Node.
- `account_picker.js`, `position_cache.js`, `screener_cache.js`, `quorum_cache.js`
  wrap every sessionStorage key in `scopedKey()`.
- `base.html`: two-segment switch next to the account picker; the inline script
  that shows the banner also marks the active segment; a module script wires clicks to `switchMode`.
  Also fixes the Disconnect button's missing `>`.
- `src/auth/router.py`: callback and dev-login call `sessionStorage.removeItem('demo_mode')` before storing the token.
- `data_use.html`: one row for demo mode state (FR-409).

## Constitution Check

- I Privacy: all state remains in sessionStorage; no new store. ✅
- II Security: no new endpoint; OAuth untouched; demo path still sends no token. ✅
- III/IV: this spec committed first; tests written and seen failing before code. ✅
- V Simplicity: one helper (`scopedKey`), no new abstraction layer. ✅
- VI UI: switch is two small buttons that fit the existing nav on mobile. ✅

## Complexity Tracking

None.
