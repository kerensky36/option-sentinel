# Quickstart: ThinkorSwim-Style UI Redesign

## Prerequisites

Start the development server:

```bash
source .venv/bin/activate
uvicorn src.api.main:app --reload --port 8000
```

---

## Verify the type scale config

### 1. Check Tailwind config (DevTools)

Open any authenticated page, open DevTools → Console, run:

```javascript
tailwind.config.theme.extend.fontSize
```

Expected output:
```json
{
  "xs":   ["9px",  {"lineHeight": "1.4"}],
  "sm":   ["11px", {"lineHeight": "1.4"}],
  "base": ["12px", {"lineHeight": "1.5"}],
  "lg":   ["13px", {"lineHeight": "1.4"}],
  "xl":   ["14px", {"lineHeight": "1.4"}],
  "2xl":  ["16px", {"lineHeight": "1.3"}],
  "3xl":  ["18px", {"lineHeight": "1.3"}]
}
```

### 2. Verify zero inline font-size overrides

In DevTools → Console on each page:

```javascript
document.querySelectorAll('[style*="font-size"]').length
```

Expected: `0`

---

## Manual visual checks — Desktop (1440px)

### Positions page (`/`)

| Element | Expected size | How to verify |
|---------|---------------|---------------|
| "Positions Dashboard" toolbar label | Very small, ~9px | Inspect → Computed → font-size |
| Refresh button text | ~9px | Same |
| Table column headers (Symbol, Underlying…) | ~9px, uppercase | Same |
| Table cell content (strike, expiry, P&L) | ~11px | Same |
| Thesis badge text | ~9px | Same |

### Screener page (`/screener`)

| Element | Expected size | How to verify |
|---------|---------------|---------------|
| "Covered Call Screener" toolbar | ~9px | Inspect |
| Scoring card titles (IV Rank, Yield Score, Delta Safety) | ~11px bold | Inspect |
| Scoring card body text | ~9px | Inspect |
| Screener table column headers | ~9px uppercase | Inspect |
| Screener table cells | ~11px | Inspect |
| Status badges (Recommended/Suppressed/No Data) | ~9px | Inspect |

### Login page (`/auth/login`)

| Element | Expected size | How to verify |
|---------|---------------|---------------|
| "Connect Your Account" heading | ~13px | Inspect |
| Body paragraph text | ~11px | Inspect |
| Checklist items (✓ bullets) | ~9px | Inspect |
| "Connect Schwab Account" button | ~11px | Inspect |
| Footer note | ~9px | Inspect |

---

## Mobile check (375px)

Open DevTools → Toggle device toolbar → iPhone SE (375px):

1. Login page: Connect button fully visible, no horizontal scroll, all text legible
2. Dashboard: Mobile nav strip visible at bottom with Positions / CC Screener links
3. Screener: Mobile nav visible; table scrolls horizontally (expected for wide tables)
4. No text appears below 9px visually (verify via Computed font-size in DevTools)

---

## Regression check

Run the full backend test suite to confirm no regressions:

```bash
pytest tests/ -q
```

Expected: all tests pass (this is a frontend-only change).

---

## Density comparison

Open the Screener page and compare against a ThinkorSwim screenshot.
The screener table should show a minimum of 8 rows without vertical scrolling on a 1080px display.
Column headers and cell values should be visually similar in density to TOS's options chain view.
