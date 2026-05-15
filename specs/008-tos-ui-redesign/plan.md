# Implementation Plan: ThinkorSwim-Style UI Redesign

**Branch**: `008-tos-ui-redesign` | **Date**: 2026-05-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/008-tos-ui-redesign/spec.md`

## Summary

Reset a broken Tailwind font scale (xs=15px / sm=18px / base=20px — artefact of two
consecutive inflate-all commits) back to terminal density (xs=9px / sm=11px / base=12px
/ lg=13px) and eliminate all ~38 scattered `style="font-size:Xpx"` inline overrides
across 4 HTML templates, 3 partials, and 3 JS files. Result: zero inline font-size
overrides in the rendered DOM, consistent 3-tier typographic scale on every page, and
visual density equivalent to a professional trading terminal.

## Technical Context

**Language/Version**: Python 3.14 (backend, no changes); Vanilla JS ES modules (frontend)
**Primary Dependencies**: Tailwind CSS v3 (CDN, inline `<script nonce>` config block); Jinja2 templates; no build step
**Storage**: N/A — frontend-only typography change
**Testing**: pytest (90 backend tests used as regression check); manual browser inspection for acceptance
**Target Platform**: Web browser (Chromium / Firefox / Safari); Cloud Run (backend) + Firebase Hosting (frontend)
**Project Type**: Web application
**Performance Goals**: No new backend load — purely client-side CSS class and config changes
**Constraints**: No build step; Tailwind config must be duplicated in `base.html` and standalone `login.html` (separate `<head>`)
**Scale/Scope**: 10 files changed; 0 new files; ~38 inline style attribute removals

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Privacy-First | ✅ PASS | No user data touched; pure styling change |
| II. Security-First | ✅ PASS | No new surfaces, routes, or data flows; removing inline style attrs reduces HTML surface |
| III. Spec-Before-Code | ✅ PASS | spec.md, research.md, data-model.md committed before implementation |
| IV. Test-First | ✅ PASS | Frontend-only — no backend logic changes; backend suite (90 tests) used as regression gate per SC-006 |
| V. Simplicity Boundary | ✅ PASS | No new abstractions; change is pure subtraction (remove overrides) |
| VI. Visual & Responsive UI | ✅ PASS | This IS the visual story — density, consistency, mobile legibility |

**Complexity Tracking**: No violations; table omitted.

## Project Structure

### Documentation (this feature)

```text
specs/008-tos-ui-redesign/
├── plan.md              ← this file
├── research.md          ← font scale decisions and rationale
├── data-model.md        ← Type Scale entity definition (3-tier contract)
├── quickstart.md        ← browser verification steps (DevTools + manual)
├── tasks.md             ← task list (10 tasks, all complete)
└── checklists/
    └── requirements.md  ← spec quality checklist
```

### Source Code (files changed)

```text
frontend/
├── templates/
│   ├── base.html                       ← Tailwind fontSize config + CSS-block + 6 inline removals
│   ├── login.html                      ← Tailwind fontSize config + body CSS + 8 inline removals
│   ├── dashboard.html                  ← 8 inline removals
│   ├── screener.html                   ← 8 inline removals
│   └── partials/
│       ├── thesis_cards.html           ← badge + stats inline removals
│       ├── screener_table.html         ← status badge + state inline removals
│       └── positions_table.html        ← empty-state inline removal
└── static/
    └── js/
        ├── positions_ui.js             ← 8 JS template string inline removals
        ├── screener_ui.js              ← 3 statusBadge() inline removals
        └── thesis_ui.js               ← 4 inline removals in renderThesisList()

src/      (backend — zero changes)
tests/    (backend — regression verification only; all 90 pass)
```

**Structure Decision**: Web application layout (Option 2). Backend untouched. All changes are
in `frontend/` — specifically Tailwind config, CSS-block pixel values, and inline style attribute removal.

## Type Scale Contract

The single source of truth for all font sizes. Defined once in `base.html`'s Tailwind config
block (and duplicated verbatim in `login.html` which has its own `<head>`).

| Tier | Tailwind class | px | Line height | Usage |
|------|---------------|-----|-------------|-------|
| 1 — label | `text-xs` | 9px | 1.4 | Badge labels, column headers, toolbar text, button text, footnotes, nav section labels |
| 2 — base | `text-sm` | 11px | 1.4 | Table cells, body copy, inputs, nav items, placeholder text |
| 3 — heading | `text-lg` | 13px | 1.4 | Page section headings, scoring card titles |

**Rule**: No inline `style="font-size:..."` anywhere. No fourth tier.

## Implementation Approach

### Phase 0 — Research
See [`research.md`](research.md). Six decisions documented:
1. Target px values (xs=9/sm=11/base=12/lg=13)
2. Three-tier semantic mapping
3. Mobile font floor (no responsive overrides needed at 9px minimum)
4. login.html Tailwind config duplication strategy
5. CSS-block rule alignment
6. JS inline style removal strategy

### Phase 1 — Design
See [`data-model.md`](data-model.md) and [`quickstart.md`](quickstart.md).
- Type Scale entity defined as a design contract (not a stored model)
- No API contracts — frontend-only change
- Quickstart documents DevTools verification steps and manual visual checks

### Phase 2 — Implementation (complete)

**Execution order** (per `tasks.md`):

1. **T001 + T002** (parallel): Fix Tailwind `fontSize` config in `base.html` and `login.html`; align CSS-block values
2. **T003**: Remove HTML inline overrides from `base.html` nav/buttons/sidebar
3. **T004–T008** (parallel): Remove inline overrides from `login.html`, `dashboard.html`, `screener.html`, `positions_ui.js`, `screener_ui.js`
4. **T009**: Manual mobile verification at 375px and 768px
5. **T010**: Full backend regression `pytest tests/ -q` — 90/90 passed

All 10 tasks complete. Zero inline font-size overrides remain in the codebase.
