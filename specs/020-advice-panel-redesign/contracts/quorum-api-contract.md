# Quorum API Contract — spec 020

Extends `specs/018-fundamentals-first-quorum/contracts/quorum-api-contract.md`. Anything not listed here is unchanged.

## POST /api/quorum/vote (v3 additions)

The request, validation, status codes, 60 s limit and 5/min rate limit are all unchanged.

**200 response additions**:

```json
{
  "verdict": "ROLL",
  "votes": [
    {
      "seat": "strike_assignment",
      "lens": "Strike & Assignment",
      "action": "ROLL",
      "confidence": 0.6,
      "roll_direction": "out",
      "rationale": "…",
      "abstained": false,
      "cited_figures": [
        {"name": "leg1_moneyness", "label": "Distance", "display": "1.3%"},
        {"name": "leg1_prob_itm", "label": "P(ITM)", "display": "31%"}
      ]
    }
  ],
  "summary_token": "eyJ2IjoxLC….3q9c…"
}
```

- `cited_figures`: 0–5 per vote; `[]` when abstained.
- `summary_token`: `null` when the verdict is NO_QUORUM or the server has no seal key. Otherwise an opaque string (≤ 20,000 chars) that the browser returns unchanged and never stores.

## POST /api/quorum/summary (new)

**Auth**: `Authorization: Bearer <schwab token>`, verified with Schwab as on the vote route.

**Rate limit**: 5 requests per minute per client (its own bucket).

**Request** (`application/json`, ≤ 24 KiB, no other fields allowed):

```json
{ "summary_token": "eyJ2IjoxLC….3q9c…" }
```

**Order of checks**:

1. Quorum not configured (017 FR-014), or `QUORUM_SEAL_KEY` unset → **503** `{"detail": "Quorum summary is not configured on this server"}`
2. Body too large, bad JSON, missing or extra field → **422** `{"detail": "Invalid summary request", "fields": [...]}` (locations only, never values)
3. Bearer missing or rejected → **401**; Schwab check failed → **502** (existing security logging)
4. Bad MAC, undecodable or invalid payload, expired or future `issued_at`, or NO_QUORUM → **403** `{"detail": "Summary request rejected"}`. No model call is made, and the body never says which check failed.
5. Summariser runs (10 s budget); the whole route completes within 15 s.

**200 responses**:

```json
{
  "status": "ok",
  "trimmed": false,
  "summary": {
    "title": "Roll the spread out one cycle, keeping the strikes.",
    "explanation": "The spread has banked 38% of its $145 max profit with 12 d left …",
    "why": ["Time decay: 38% captured with 12 d left; rolling now collects fresh premium."],
    "dissent": "Greeks and Volatility would hold …"
  }
}
```

```json
{ "status": "unavailable", "trimmed": false, "summary": null }
```

`unavailable` covers a model error, a timeout, malformed output, and a guard discard (D-307). It is a 200 because the request itself was valid; the panel shows "Summary unavailable".

**Headers**: the same security headers and `Cache-Control: no-store` as the vote route.

## Service APIs (Python)

```python
# src/services/figure_catalog.py  (pure)
def build(ctx: PositionContext) -> dict[str, Figure]: ...
def add_tally(catalog: dict[str, Figure], tally: list[TallyEntry], votes: list[AnalystVote]) -> dict[str, Figure]: ...
def resolve_cited(names: list[str], catalog: dict[str, Figure]) -> list[CitedFigure]: ...

# src/services/quorum_summary.py
def seal(result: QuorumResult, catalog: dict[str, Figure], *, key: bytes, now: datetime) -> str | None: ...
def unseal(token: str, *, key: bytes, now: datetime) -> SummaryPayload:  # raises TokenRejected
async def summarise(payload: SummaryPayload, *, model, timeout: float = 10.0) -> QuorumSummary: ...
def guard(draft: SummaryDraft, payload: SummaryPayload) -> tuple[QuorumSummary, str | None]: ...  # (result, reason)
def seal_key() -> bytes | None: ...  # QUORUM_SEAL_KEY, None if unset or < 32 bytes
```

## Frontend module APIs

```js
// quorum_ring.js (pure)
export const VOTE_COLORS = { CLOSE: '#e8703a', HOLD: '#8c93a8', ROLL: '#3aa8e0', NONE: '#3a3a4a' };
export function ringSvg(result, { animate = false } = {}) { /* → SVG string */ }

// quorum_ui.js
export function adviceButton(id) { /* → <button …>ADVICE(Agentic)</button> HTML */ }
export function renderResult(result) { /* → panel HTML with summary area in 'pending'|'fixed'|'unavailable' */ }
export function renderSummary(state, summary) { /* → summary area HTML */ }
export function initQuorum(container, positionData) { /* unchanged signature */ }
```
