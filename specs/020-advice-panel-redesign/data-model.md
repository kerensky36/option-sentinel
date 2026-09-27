# Data Model: Advice Panel Redesign

All entities exist only for the life of one request or one open panel. Nothing is stored (017 FR-015, constitution Storage rule).

## FigureCatalog (server, `figure_catalog.py`)

An ordered mapping `name → Figure`, built per vote request from the `PositionContext` (018) and extended with the tally.

| Field | Type | Rule |
|-------|------|------|
| `name` | str | `^[a-z][a-z0-9_]{0,39}$`, unique in the catalog |
| `label` | str | ≤ 24 chars, e.g. "IV/RV", "Captured" |
| `value` | float | Raw value; never NaN or infinite |
| `display` | str | Formatted by kind (below); this is the only text a number is ever shown as |

**Names** (included only when the value is available, 018 FR-105):

- Position: `net_delta`, `net_theta_day`, `net_vega`, `max_profit`, `max_loss`, `captured_pct`, `breakeven_1`, `breakeven_2`, `dte`
- Per leg (n = 1..4, leg order as sent): `leg{n}_strike`, `leg{n}_spot`, `leg{n}_iv`, `leg{n}_rv`, `leg{n}_iv_rv`, `leg{n}_moneyness`, `leg{n}_prob_itm`
- Tally (added after voting): `votes_close`, `votes_hold`, `votes_roll`, `valid_votes`, `seats`, `confidence_<seat_id>` for each voting seat

**Display kinds**:

| Kind | Example | Used for |
|------|---------|----------|
| money | `$1,234` / `$572.40` (2 dp under $1,000) | max profit/loss, breakevens, strike, spot, $ theta, $ vega |
| pct | `38%` / `1.3%` (1 dp under 10%) | captured, IV, RV, moneyness, P(ITM), confidence |
| ratio | `1.08×` | IV/RV |
| shares | `+22 sh` | net delta |
| days | `12 d` | dte |
| count | `3` | tally figures |

## CitedFigure

A catalog figure a seat relied on. `{name, label, display}` is copied from the catalog. At most 5 per vote, with no duplicates. Unknown names are dropped silently (counted in the INFO log).

## AnalystBallot (seat model output) — extended

Adds `cited: list[str]` (default `[]`, truncated to 5). All 018 fields and validators are unchanged.

## AnalystVote (result) — extended

Adds `cited_figures: list[CitedFigure]` (default `[]`; always empty when abstained).

## QuorumResult (vote response) — extended

Adds `summary_token: str | None`:
- `null` when the verdict is NO_QUORUM or `QUORUM_SEAL_KEY` is not configured;
- otherwise a SummaryToken string.

All other fields are as in spec 018.

## SummaryToken (opaque to the browser)

The string `base64url(payload) + "." + base64url(HMAC_SHA256(QUORUM_SEAL_KEY, base64url(payload)))`. The total length is at most 20,000 chars.

**Payload** (canonical JSON, `sort_keys=True`, separators `(",", ":")`):

| Field | Type | Notes |
|-------|------|-------|
| `v` | int | Token format version, `1` |
| `issued_at` | ISO-8601 UTC | Server clock when the vote result was built |
| `underlying_symbol` | str | For the summary prompt only |
| `verdict` | QuorumVerdict | Never `NO_QUORUM` (such results get no token) |
| `roll_direction` | RollDirection \| null | Shared by all ROLL voters, else null (D-307) |
| `tally` | list[TallyEntry] | As in the result |
| `votes` | list[{seat, lens, action, confidence, roll_direction, rationale, cited: [names], abstained}] | |
| `figures` | FigureCatalog incl. tally figures | name → {label, display}; raw values omitted |

**Validation on unseal**, where any failure means 403 and no model call:
- the MAC matches (constant-time comparison);
- the payload decodes and parses into the schema above with `extra="forbid"`;
- `v == 1`;
- `now − 15 min ≤ issued_at ≤ now + 2 min`;
- the verdict is not NO_QUORUM.

## SummaryDraft (summariser model output schema)

| Field | Type | Limit |
|-------|------|-------|
| `title` | str | stripped, ≤ 120 chars |
| `explanation` | str | ≤ 600 chars (the prompt asks for ≤ 3 sentences) |
| `why` | list[str] | 1–4 items, each ≤ 200 chars |
| `dissent` | str | ≤ 400 chars |

## QuorumSummary (summary response body)

| Field | Type | Notes |
|-------|------|-------|
| `status` | `"ok"` \| `"unavailable"` | |
| `summary` | {title, explanation, why[], dissent} \| null | Present only when `ok`; placeholders already filled; `why` has ≥ 1 item |
| `trimmed` | bool | True if the guard removed any bullet or dissent sentence |

## Panel summary state (browser)

`pending` ("Writing summary…") → `ok` | `unavailable`. NO_QUORUM goes straight to `fixed` ("Only N of 5 analysts voted — no recommendation."). A state is discarded when the panel closes.

## Vote palette (shared constant, `quorum_ring.js`)

| Vote | Colour | Extra cue |
|------|--------|-----------|
| HOLD | `#8c93a8` | — |
| ROLL | `#3aa8e0` | — |
| CLOSE | `#e8703a` | diagonal hatch on filled areas |
| Abstain | `#3a3a4a` | "ABSTAIN" label, empty wedge |
