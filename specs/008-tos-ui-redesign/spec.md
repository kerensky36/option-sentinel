# Feature Specification: ThinkorSwim-Style UI Redesign

**Feature Branch**: `008-tos-ui-redesign`
**Created**: 2026-05-15
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Dense Information Layout on Desktop (Priority: P1)

As a trader using Option Sentinel on a desktop browser, I want the UI to display maximum data density with a professional, terminal-grade aesthetic — small, crisp monospace type, tight table rows, and no wasted whitespace — so that I can scan positions and screener results at a glance without scrolling excessively, just like I would in ThinkorSwim.

**Why this priority**: The core value of the app is displaying financial data. Oversized fonts make the tables useless — a single position row should be scannable in one eye movement, not require scrolling. This is the most critical regression to fix.

**Independent Test**: Open the Positions and Screener pages on a 1440px desktop. All table rows, column headers, and badges must be visually consistent and dense. No font size should exceed 12px in table cells or badge labels.

**Acceptance Scenarios**:

1. **Given** the Positions page is open on desktop, **When** the page renders, **Then** all table cells use a consistent small monospace font (visually equivalent to ThinkorSwim table density).
2. **Given** the Screener page is open on desktop, **When** results are present, **Then** the score, status badges, and all numeric columns are rendered at the same scale as table cells — no mixed sizing.
3. **Given** any page with buttons or nav items, **When** the user views the page, **Then** all interactive elements use the same typographic scale — no button is visibly larger than surrounding text.
4. **Given** the nav sidebar is visible, **When** the user views it, **Then** nav labels, section headings, and footer text all use the same compact scale.

---

### User Story 2 — Consistent Typography Across All Pages (Priority: P1)

As a trader, I want every piece of text on every page to come from a single, clearly defined type scale — three tiers at most — so that the interface feels coherent and professional rather than assembled from mismatched font sizes.

**Why this priority**: The current codebase has inline `style="font-size:Xpx"` overrides scattered across templates and JS render functions that fight the Tailwind config. This causes inconsistency that signals amateur quality even before the actual values are corrected.

**Independent Test**: Inspect the DOM on each page (Login, Dashboard, Screener). All visible text elements must derive their font size from exactly one of three CSS classes — no inline `font-size` style attributes anywhere in the rendered HTML.

**Acceptance Scenarios**:

1. **Given** any page, **When** the browser DevTools font inspector is used, **Then** no element has a `font-size` applied via inline style — all sizes come from CSS classes.
2. **Given** the Login page, **When** it renders, **Then** the headline, body copy, button labels, and footnotes each belong to one of three clearly distinguishable text tiers (large/medium/small).
3. **Given** the Screener page header and the Positions page header, **When** compared side by side, **Then** they use identical font-size classes and visual weight.
4. **Given** status badges (Recommended / Suppressed / No Data), **When** rendered in the screener table, **Then** badge text matches the smallest tier — consistent with table cell text.

---

### User Story 3 — Responsive Layout on Tablet and Mobile (Priority: P2)

As a trader checking positions on a phone or tablet, I want the app to remain usable — navigation accessible, key data visible without horizontal scrolling on summary views — without sacrificing the dense desktop layout.

**Why this priority**: The existing layout already has a mobile nav strip and responsive breakpoints. This story ensures the font and spacing changes don't break mobile legibility — the font scale must remain readable (not microscopic) on small screens.

**Independent Test**: Open each page at 375px (mobile) and 768px (tablet) viewport widths. The nav must be reachable, login must be usable, and no body text must be smaller than 10px at those breakpoints.

**Acceptance Scenarios**:

1. **Given** a 375px mobile viewport, **When** the Login page renders, **Then** the Connect button and all instructional text are fully visible and tappable without horizontal scrolling.
2. **Given** a 375px mobile viewport, **When** the Positions or Screener page is open, **Then** the mobile nav strip is visible and all nav links are reachable.
3. **Given** a 768px tablet viewport, **When** the sidebar is expected to appear (desktop breakpoint), **Then** it renders correctly with the same compact type scale as desktop.
4. **Given** any breakpoint, **When** the page loads, **Then** no text element is rendered below 10px — terminal density must not cross into illegibility.

---

### Edge Cases

- A page with no data (empty positions, empty screener results): the empty-state message must use the standard type scale, not a one-off large heading.
- Very long ticker symbols or thesis names: text must truncate or wrap without breaking table layout.
- The "How Scoring Works" disclosure panel on the Screener page: body text inside the panel must use the standard scale, not a separate size.
- Zoom levels: at 150% browser zoom, the layout must not break (overflow, overlap).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All font sizes across the application MUST be defined in a single Tailwind font-scale configuration — three tiers maximum (e.g., label/body/heading). No inline `style="font-size:..."` attributes are permitted anywhere in HTML templates or JavaScript-generated HTML.
- **FR-002**: The base (body/table-cell) font size MUST be in the 10–12px range to achieve professional trading-terminal density on desktop.
- **FR-003**: The smallest tier (badge labels, column headers, footnotes) MUST be in the 9–11px range.
- **FR-004**: The largest tier (page headings, section titles) MUST be in the 13–15px range.
- **FR-005**: All pages (Login, Dashboard/Positions, Screener) MUST use the same typographic scale with no per-page overrides.
- **FR-006**: Table rows on the Positions and Screener pages MUST maintain their current dark-theme colour coding (green/red for P&L, amber for warnings, status badges) — only the size changes, not the colour semantics.
- **FR-007**: On mobile viewports (< 640px), font sizes MUST NOT drop below 10px on any visible element to preserve legibility.
- **FR-008**: The nav sidebar (desktop), top nav bar, and mobile nav strip MUST all use the same compact typographic tier as table content.
- **FR-009**: The layout structure (sidebar, top nav, content area, table columns) MUST remain unchanged — this is a typography and spacing polish, not a layout redesign.

### Key Entities

- **Type Scale**: The three-tier font size definition (small / base / heading). Single source of truth in the Tailwind config.
- **Inline Override**: Any `style="font-size:..."` attribute in a template or JS string — all must be removed.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero inline `font-size` style attributes appear in the rendered DOM of any page (verifiable via DevTools or automated HTML inspection).
- **SC-002**: All font sizes on every page fall within the 9–15px range at 100% browser zoom on desktop.
- **SC-003**: The Positions table and Screener table each display a minimum of 8 rows without vertical scrolling on a 1080px-tall desktop display.
- **SC-004**: At 375px viewport width, all Login page interactive elements are reachable without horizontal scrolling and no text is smaller than 10px.
- **SC-005**: A visual comparison of the Screener page against a ThinkorSwim table screenshot shows equivalent information density (subjective, validated by the developer).
- **SC-006**: The existing test suite (backend unit + contract tests) continues to pass with no regressions — the changes are purely frontend.

---

## Assumptions

- Only the four pages noted by the user (base.html / nav, dashboard.html, screener.html, login.html) and any JS that generates inline HTML are in scope. No new pages, routes, or backend changes.
- The monospace font (JetBrains Mono) is kept — the redesign corrects sizes, not the typeface choice.
- The dark colour palette and ThinkorSwim-inspired colour semantics (green/red/amber) are kept exactly as-is.
- No automated visual regression test suite exists in this project. Acceptance is manual browser inspection.
- Tailwind CSS is delivered via CDN with a custom config block in base.html — no build step is required. The fix is contained to that config block and inline style removal in templates/JS.
- The three-tier scale will map to Tailwind utility names (`text-xs`, `text-sm`, `text-base` or custom equivalents) that all templates and JS can use without ambiguity.
