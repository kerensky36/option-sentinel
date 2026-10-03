# Feature Specification: Self-Hosted Styles and Strict CSP Everywhere

**Feature Branch**: `023-self-hosted-assets-strict-csp`
**Created**: 2026-10-03
**Status**: Draft
**Input**: Follow-up to the 2026-10-03 security scan (spec 022). Every page loads `https://cdn.tailwindcss.com`, a third-party script with full access to the page — including the Schwab token in sessionStorage — with no integrity check. Pages served by Firebase Hosting (the production front door) carry no Content-Security-Policy or other security headers at all; only Cloud Run responses do.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — No third-party code can read the Schwab token (Priority: P1)

**Independent Test**: Load any app page: the only scripts are from the app's own origin; no request goes to `cdn.tailwindcss.com`; the page looks the same as before.

**Acceptance Scenarios**:

1. **Given** any template, **Then** it does not reference `cdn.tailwindcss.com` and links the self-hosted stylesheet `/static/css/app.css`.
2. **Given** the self-hosted stylesheet, **Then** it is built by the pinned Tailwind CLI (v3.4.19) from the same theme the CDN config used (JetBrains Mono, the compact font sizes) and contains every utility class used in templates and JS.
3. **Given** the stylesheet is committed, **When** the build is re-run in CI, **Then** the output is identical (stale CSS fails CI).
4. **Given** the pages, **When** compared before/after in a browser, **Then** layout, fonts and colours match.

---

### User Story 2 — A strict CSP on every page, including Firebase (Priority: P1)

**Independent Test**: Fetch `/`, `/screener`, `/data-use` and `/auth/login` from Firebase Hosting: each response has a CSP whose `script-src` is `'self'` only, plus `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy` and HSTS.

**Acceptance Scenarios**:

1. **Given** the templates, **Then** none contains an inline `<script>` body; all page scripts are files under `/static/js/`.
2. **Given** Cloud Run responses, **Then** the CSP `script-src` is `'self'` plus the per-request nonce (still used by the auth hand-off pages) and no third-party host.
3. **Given** `firebase.json`, **Then** every hosted path gets `Content-Security-Policy` with `script-src 'self'`, `object-src 'none'`, `base-uri 'self'`, `form-action 'self'`, `frame-ancestors 'none'`, and the same security headers as Cloud Run.
4. **Given** the built `dist/` pages, **Then** they contain no inline script and no reference to a third-party script host.
5. **Given** the demo banner and the Demo | Live switch, **When** a page loads, **Then** they render as before (now from `/static/js/shell.js`), without a visible flash.

### Edge Cases

- `style-src` keeps `'unsafe-inline'`: templates use inline `style` attributes and `<style>` blocks. Style injection cannot read sessionStorage; removing it is out of scope.
- Google Fonts stylesheets and font files stay allowed (`style-src`/`font-src`); they are CSS and fonts, not scripts.
- Firebase Hosting rewrites `/api/**` and `/auth/**` to Cloud Run, so `connect-src 'self'` still covers API calls; Cloud Run's own CSP applies to `/auth/**` responses.

## Requirements *(mandatory)*

- **FR-601**: Templates MUST NOT load scripts from any third-party origin.
- **FR-602**: Styles MUST come from a committed, self-hosted `frontend/static/css/app.css` built by `scripts/build_css.sh` with a pinned Tailwind CLI and `tailwind.config.js`; CI MUST fail if the committed file differs from a fresh build.
- **FR-603**: Templates MUST contain no inline script bodies; page logic moves to `/static/js/shell.js` (banner, mode switch, Erase All Data) and existing modules.
- **FR-604**: The Cloud Run CSP MUST drop `https://cdn.tailwindcss.com` from `script-src`.
- **FR-605**: `firebase.json` MUST send CSP and security headers on all hosted paths, with `script-src 'self'` and no `'unsafe-inline'` or `'unsafe-eval'` for scripts.
- **FR-606**: No production runtime dependency is added (Node is build-time only; the CSS is committed).
- **FR-607**: The data-use page MUST drop `cdn.tailwindcss.com` from its list of third parties that receive request data.

## Success Criteria

- **SC-601**: Zero third-party script origins across all pages (automated test over templates, `dist/` and both CSPs).
- **SC-602**: Browser check of `/`, `/screener`, `/data-use`, `/auth/login` shows no CSP violations in the console and unchanged appearance.
