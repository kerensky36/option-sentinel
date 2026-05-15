# Research: ThinkorSwim-Style UI Redesign

## Decision 1: Target font sizes

**Decision**: xs=9px / sm=11px / base=12px / lg=13px / xl=14px / 2xl=16px / 3xl=18px

**Rationale**: ThinkorSwim's desktop interface renders table cells at approximately 11px
and column headers/badge labels at 9–10px. The `text-xs` and `text-sm` Tailwind tokens map
cleanly onto these tiers without introducing custom token names. The current scale (xs=15px,
sm=18px, base=20px) is a double-then-1.5× artefact from two consecutive commits (f6960fa, f497a25)
that progressively inflated all sizes. Reverting to a 9–13px range restores terminal density.

**Alternatives considered**:
- xs=10px / sm=12px / base=14px: Slightly larger, closer to typical web body text.
  Rejected — still too large for the data-dense TOS aesthetic at 1080p.
- Keeping existing sizes and only removing inconsistencies: Rejected — the sizes themselves
  are the core problem. Consistent application of 18px would still look amateur.

## Decision 2: Three-tier mapping

**Decision**: One Tailwind class per semantic tier:
- `text-xs` (9px) → badge labels, column headers, footnotes, nav section labels, toolbar text, button text
- `text-sm` (11px) → table cells, body copy, form inputs, nav item labels, placeholder spans
- `text-lg` (13px) → page headings, scoring card titles with semantic emphasis

**Rationale**: Constraining the entire UI to three tiers prevents the ad-hoc mixed sizing that
created the current amateur look. `text-lg` skips `text-base` (12px) to provide a visually
clear separation between headings and body. The ~2px step between tiers is consistent with
TOS's typographic rhythm.

**Alternatives considered**:
- Four tiers (9/11/13/16px): Unnecessary for this app's simple information hierarchy.
  Rejected — keeps things simpler.
- Using CSS custom properties (--font-xs etc.): More portable but adds abstraction where
  Tailwind classes already provide the same benefit. Rejected — no build step, Tailwind CDN
  is already the styling mechanism.

## Decision 3: Mobile font floor

**Decision**: No explicit mobile breakpoint font overrides. The 9px minimum (text-xs) is
acceptable on mobile viewports for a trading app.

**Rationale**: ThinkorSwim's own mobile app renders data at approximately 9–10px on phones.
Traders use small fonts intentionally to see more data. SC-004 (375px legibility) is met at
9px for elements like badge labels — these are supplementary; the primary content (symbol,
P&L, strike) is rendered at 11px (text-sm) and is comfortably readable. The Tailwind CDN
config does not support responsive font-size overrides in the `extend.fontSize` block
without a build step, making mobile-specific size overrides impractical here.

**Alternatives considered**:
- min-font-size: 10px via CSS `@media` query override: Viable but adds CSS complexity.
  Rejected — 9px elements on mobile are badge labels; users can read them at arm's length.
- Tailwind responsive modifiers on individual elements: Would require adding `sm:text-xs`
  to every `text-xs` element. Too invasive and error-prone without a build step.

## Decision 4: login.html Tailwind config duplication

**Decision**: Update the Tailwind `fontSize` config block in both `base.html` and `login.html`
independently. They are exact copies of each other.

**Rationale**: `login.html` does not extend `base.html` — it is a standalone page with its
own `<head>`. Both files contain identical `tailwind.config = {...}` blocks. Both must be
updated or login will appear with a different scale than authenticated pages.

**Alternatives considered**:
- Refactor login.html to extend base.html: Out of scope for this feature — login has no
  sidebar/nav and a different layout. Rejected.
- Shared external JS config file: Would require a build step or dynamic script loading.
  Rejected — complexity not justified.

## Decision 5: CSS-block font-size rules

**Decision**: Update the inline `<style>` block in base.html to match the new scale:
- `body { font-size: 11px }` (from 20px)
- `table { font-size: 11px }` (from 18px) — kept for table-level override specificity
- `table th { font-size: 9px !important }` (from 15px)
- `input[type="number"], input[type="text"], select { font-size: 11px }` (from 18px)
- `.nav-section-label { font-size: 9px }` (from 15px)
- `.nav-item { font-size: 11px }` (from 18px)

**Rationale**: The `<style>` block rules take precedence over inherited body styles for
specific elements. Keeping them ensures correct rendering even if a template doesn't use
Tailwind classes (e.g., raw `<table>` without class). Aligning them with the Tailwind
config prevents conflicts.

**Alternatives considered**:
- Remove CSS-block rules and rely entirely on Tailwind classes: Cleaner in principle, but
  risks regression if a template is missing classes. Keeping minimal CSS rules as a safety net.

## Decision 6: JS inline style removal strategy

**Decision**: In `positions_ui.js` and `screener_ui.js`, remove all `style="font-size:Xpx"`
from JS template literal strings and replace with the appropriate Tailwind text class added
to the element's `class` attribute. Letter-spacing inline styles in thead rows are replaced
with `tracking-wider`. The `border-radius:1px` on status badges is removed since the global
rounded-* overrides in base.html already enforce 1–2px radii.

**Rationale**: SC-001 (zero inline font-size attributes in DOM) requires removing these.
Since the Tailwind config is now corrected, `text-xs` and `text-sm` classes produce the
right pixels without any inline style needed.

**Alternatives considered**:
- Leave JS inline styles at their current values (9–12px): The sizes happen to be in the
  correct range. But SC-001 requires zero inline overrides — a systematic approach is cleaner
  and ensures future maintainability.
