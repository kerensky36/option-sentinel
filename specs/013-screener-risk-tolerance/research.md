# Research: Screener Risk Tolerance Controls

**Feature**: 013-screener-risk-tolerance  
**Date**: 2026-05-17

## Decision 1: Where scoring happens — server vs client

**Decision**: Server scores under Balanced profile and returns the result; client re-scores under non-Balanced profiles using raw candidates stored in sessionStorage.

**Rationale**: The initial page render must be fast and correct with no JS required. The server continues to return a fully-scored Balanced result (same as today). Non-Balanced profiles are pure client-side re-scores from cached candidates — zero additional API calls. This keeps the server contract backward-compatible (existing fields unchanged) and adds only one new field (`candidates`).

**Alternatives considered**:
- Server-only scoring with profile param: server re-runs full screener per profile change → Schwab API calls on every toggle, unacceptable latency.
- Client-only scoring always: no server-computed score, initial render requires JS to run — breaks graceful degradation and adds complexity.

## Decision 2: Candidate selection algorithm — nearest-delta vs score-maximize

**Decision**: "Pick candidate closest to target delta within DTE window, then score" — matching the existing server algorithm (`min(liquid, key=lambda o: abs(o["delta"] - target_delta))`).

**Rationale**: Ensures the Balanced profile produces byte-identical results to the current server output — making it the zero-regression baseline (FR-005, SC-002). Score-maximization would be more globally optimal but would cause Balanced to differ from today's server output, breaking the regression guarantee.

**Alternatives considered**:
- Score-maximize across all candidates: better theoretical quality but invalidates the "Balanced = current" guarantee.

## Decision 3: DTE fetch window

**Decision**: Widen `_fetch_call_chain` date range to 7–60 DTE. Keep `_DTE_MIN` / `_DTE_MAX` constants renamed as `_FETCH_DTE_MIN = 7` / `_FETCH_DTE_MAX = 60`. The Balanced profile's DTE filter (30–45) is applied client-side, not server-side.

**Rationale**: A single wider fetch returns all candidates in one Schwab API call per ticker (already parallelised). The client filters by profile DTE window when re-scoring. Total Schwab calls unchanged — just the date range in each call widens.

**Alternatives considered**:
- Multiple fetches per ticker (one per DTE preset): doubles/triples Schwab calls, negates the parallelisation benefit.
- Dynamic fetch width based on profile: requires server to know the active profile — violates stateless design.

## Decision 4: `candidates` field format

**Decision**: Add `candidates: list[dict]` to `ScreenerResultView`. Each dict: `{delta, bid, dte, strike, expiry, open_interest}`. Only liquid candidates (bid ≥ $0.05, OI ≥ 100) are included.

**Rationale**: Minimal payload — only the fields the client needs to re-score. Pre-filtered to liquid options only, so the client doesn't need to re-apply liquidity rules. Empty list for tickers with no liquid options.

**Alternatives considered**:
- Separate `/api/screener/candidates` endpoint: adds round-trip, defeats purpose of client-side re-scoring.
- Raw full chain data: far larger payload, client would need to re-apply liquidity logic.

## Decision 5: Profile preset parameter values

**Decision**:

| Profile | Target Delta | DTE Min | DTE Max | Yield Weight | Safety Weight | IV Weight |
|---------|-------------|---------|---------|--------------|---------------|-----------|
| Conservative | 0.15 | 30 | 60 | 0.15 | 0.35 | 0.50 |
| Balanced | 0.25 | 30 | 45 | 0.30 | 0.20 | 0.50 |
| Aggressive | 0.35 | 7 | 30 | 0.40 | 0.10 | 0.50 |

**Rationale**: Balanced exactly matches the current server defaults (no regression). Conservative shifts OTM (lower delta, longer DTE, safety-weighted). Aggressive shifts near-money (higher delta, short DTE, yield-weighted). IV rank stays at 50% per the agreed assumption.

## Decision 6: Session persistence mechanism

**Decision**: Active profile name stored in `sessionStorage` under key `screener_profile`. Defaults to `"balanced"` if absent.

**Rationale**: Consistent with the project's sessionStorage-only policy (constitution Principle I). Clears automatically on tab close. No localStorage, no cookies.

## Decision 7: Fine-grained sliders UI pattern (P2)

**Decision**: Single "Safety ↔ Yield" range input (0–100) representing what fraction of the non-IV 50% goes to yield. The safety weight is derived: `safetyWeight = (1 - sliderValue/100) * 0.5`, `yieldWeight = (sliderValue/100) * 0.5`. Separate range inputs for target delta (0.10–0.45, step 0.01) and DTE range (min 7, max 60, step 1, two thumbs for range).

**Rationale**: Avoids the 3-weight normalization problem entirely. User controls one axis; IV is fixed; safety is the remainder. Simple to implement and explain.
