# Data Model: ThinkorSwim-Style UI Redesign

*No server or client data models are introduced or modified by this feature.
This file documents the single logical entity that governs the change: the Type Scale.*

## Logical Entity: Type Scale

**Not a stored entity — a design contract enforced via Tailwind config.**

| Tier | Tailwind token | Pixel size | Line height | Semantic use |
|------|---------------|-----------|-------------|--------------|
| 1 — label | `text-xs` | 9px | 1.4 | Badge labels, table column headers, form labels, nav section headings, toolbar labels, button text, footnotes |
| 2 — base | `text-sm` | 11px | 1.4 | Table cell content, body copy, form input values, nav item text, placeholder text |
| 3 — heading | `text-lg` | 13px | 1.4 | Page section headings, scoring card titles |

### Constraint: No fourth tier

The only permitted font-size mechanism is a Tailwind text-* utility class corresponding to
one of the three tiers above. Inline `style="font-size:..."` attributes are forbidden
in all HTML templates and JS-generated HTML strings.

### Responsive behaviour

No tier changes at breakpoints. The 9px minimum is intentional and consistent with
professional trading terminal conventions. At 375px mobile viewport, label-tier elements
(text-xs at 9px) remain readable for supplementary data; primary data (symbols, strikes,
P&L values) use the base tier (11px).

## Files affected

| File | Change |
|------|--------|
| `frontend/templates/base.html` | Tailwind fontSize config + CSS-block px values |
| `frontend/templates/login.html` | Tailwind fontSize config (duplicate) + CSS-block |
| `frontend/templates/dashboard.html` | Remove inline font-size overrides |
| `frontend/templates/screener.html` | Remove inline font-size overrides |
| `frontend/static/js/positions_ui.js` | Remove inline font-size from JS HTML strings |
| `frontend/static/js/screener_ui.js` | Remove inline font-size from JS HTML strings |
