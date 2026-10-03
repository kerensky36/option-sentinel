# Tasks: Self-Hosted Styles and Strict CSP Everywhere

**Tests**: Required (Constitution IV, Principle II); run and see them fail before implementing.

- [ ] T001 `tests/unit/test_strict_csp.py`: no CDN or inline scripts in templates; `app.css` linked and present with key classes; Cloud Run CSP has no third-party script host; `firebase.json` headers; built `dist/` pages clean; data-use page has no Tailwind CDN row.
- [ ] T002 Tailwind config, input CSS, `scripts/build_css.sh`; build and commit `app.css`.
- [ ] T003 Templates: stylesheet link; `shell.js` + `shell_actions.js`; dashboard/screener module tags.
- [ ] T004 `_CSP` and `firebase.json` headers; data-use page.
- [ ] T005 CI stale-CSS check; full `pytest -q`; Chromium visual + console CSP check (before/after screenshots).
