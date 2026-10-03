# Implementation Plan: Self-Hosted Styles and Strict CSP Everywhere

**Branch**: `023-self-hosted-assets-strict-csp` | **Spec**: [spec.md](./spec.md)

## Design

- `tailwind.config.js`: theme copied from the inline CDN config; `content` = `frontend/templates/**/*.html`, `frontend/static/js/**/*.js`.
- `frontend/tailwind.input.css`: `@tailwind base; @tailwind components; @tailwind utilities;`.
- `scripts/build_css.sh`: `npx --yes tailwindcss@3.4.19 -c tailwind.config.js -i frontend/tailwind.input.css -o frontend/static/css/app.css --minify`. Output committed.
- Templates: replace the CDN `<script>` and the inline config with `<link rel="stylesheet" href="/static/css/app.css">`.
- `frontend/static/js/shell.js` (classic script for the banner/switch marking so it runs before paint; module part imports auth.js for switch + erase handlers). Split: `shell.js` (classic, early) and `shell_actions.js` (module, end of body).
- dashboard/screener: `<script type="module" src="/static/js/positions_ui.js">` / `screener_ui.js`.
- `src/api/main.py` `_CSP`: `script-src 'self' 'nonce-{nonce}'`.
- `firebase.json`: `headers` entry for `**` with the static CSP and security headers.
- CI: Node step runs `scripts/build_css.sh` then `git diff --exit-code frontend/static/css/app.css`.

## Constitution Check

- I Privacy: removes a third party that could read the token. Data-use page updated (FR-607). ✅
- II Security: tests first for every control (no CDN, no inline scripts, both CSPs, Firebase headers). ✅
- V Simplicity: no runtime dependency; one generated, committed CSS file. ✅
- VI UI: appearance unchanged; verified in Chromium. ✅
