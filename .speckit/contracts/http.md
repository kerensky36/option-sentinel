# HTTP Contracts: Option Sentinel

**Date**: 2026-04-29 | **Branch**: `001-option-sentinel-monitor`
**Base URL**: `http://localhost:8000`

All HTML endpoints return `text/html`. All JSON endpoints return `application/json`.
The app is single-user, local-only — no authentication on routes.

---

## Dashboard Routes (HTML / HTMX)

### GET /
Full dashboard page.

**Response**: `200 text/html` — renders `dashboard.html` with current positions,
thesis groups, binary event banner state, and polling status.

---

### GET /partials/positions
HTMX-swappable positions table fragment. Called on SSE `refresh` event.

**Response**: `200 text/html` — renders `partials/positions_table.html`.

---

### GET /sse
Server-Sent Events stream. Pushed after each successful poll cycle.

**Response**: `text/event-stream`

```
event: refresh
data: {"polled_at": "2026-04-29T14:35:00Z", "position_count": 4}

event: re_auth_required
data: {"message": "Schwab refresh token expires in 18 hours. Re-authenticate."}
```

The client attaches with `hx-ext="sse"` and `sse-connect="/sse"`. On `refresh`
event, HTMX triggers `GET /partials/positions`.

---

## Thesis Endpoints

### POST /thesis
Create a new thesis group.

**Request body** (form or JSON):
```json
{
  "name": "NVDA IV Crush",
  "template_type": "iv_crush",
  "description": "Sell premium before earnings; expect IV to collapse post-announcement"
}
```

**Response**:
- `201 text/html` — renders updated `partials/thesis_panel.html` (HTMX OOB swap)
- `422` — validation error

---

### PUT /thesis/{thesis_id}/alignment
Update alignment rating on a thesis group.

**Request body**:
```json
{ "alignment_rating": "aligned" }
```
Valid values: `aligned`, `partially_aligned`, `misaligned`, `unrated`

**Response**:
- `200 text/html` — renders updated thesis row HTML (HTMX swap target)
- `404` — thesis not found

---

### DELETE /thesis/{thesis_id}
Delete a thesis group. Moves member positions to Unassigned.

**Response**:
- `200 text/html` — renders updated `partials/thesis_panel.html`
- `404` — thesis not found

---

## Position Endpoints

### POST /positions/{position_id}/assign
Assign a position to a thesis group (or unassign by passing `null`).

**Request body**:
```json
{ "thesis_id": "uuid-or-null" }
```

**Response**:
- `200 text/html` — renders updated `partials/position_row.html` (HTMX OOB swap)
- `404` — position or thesis not found

---

### POST /positions/{position_id}/exit-goals
Set or update exit goals for a position.

**Request body**:
```json
{
  "profit_target_pct": 50.0,
  "dte_threshold": 21,
  "underlying_price_target": 520.00,
  "price_target_direction": "above"
}
```
All fields are optional. At least one must be non-null.

**Response**:
- `200 text/html` — renders updated `partials/position_row.html`
- `404` — position not found
- `422` — no goal fields provided

---

## Binary Event Flag Endpoints

### POST /binary-event/raise
Raise the binary event flag. Immediately triggers full-exit email alert.

**Response**:
- `200 text/html` — renders `partials/binary_banner.html` (active state)

---

### POST /binary-event/clear
Clear the binary event flag.

**Response**:
- `200 text/html` — renders `partials/binary_banner.html` (inactive state)

---

## System Endpoints

### GET /health
Liveness check.

**Response**:
```json
{
  "status": "ok",
  "last_poll": "2026-04-29T14:35:00Z",
  "db": "ok",
  "schwab_auth": "ok | re_auth_required"
}
```
