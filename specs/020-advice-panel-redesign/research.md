# Research: Advice Panel Redesign

Decisions for spec 020. They continue from 018's D-101–D-114, numbered D-301 onward to match the FR-3xx numbering.

## D-301 — Summary delivered by a second request

- **Decision**: `/api/quorum/vote` returns without waiting for a summary. The browser then posts to `/api/quorum/summary`.
- **Rationale**: This is the user's clarification (spec, Session 2026-09-27). The verdict is never delayed and 018 FR-118's 60 s limit stays as it is.
- **Alternatives**:
  - One combined response: every verdict would be up to 10 s slower.
  - Streaming (SSE or chunked): adds a streaming client, proxy buffering concerns on Cloud Run and Firebase, and harder tests, for the same user experience.

## D-302 — Stateless trust via a signed opaque token

- **Decision**: The vote route builds the summariser's input (verdict, tally, votes with cited-figure names, the figure catalog, `issued_at`). It serialises that input as canonical JSON (`sort_keys=True`, compact separators) and base64url-encodes it. The token is that encoding plus `.` plus the base64url HMAC-SHA256 of it under `QUORUM_SEAL_KEY`. The browser treats the token as an opaque string and returns it unchanged. The summary route recomputes the MAC, compares it with `hmac.compare_digest`, decodes the payload, and checks that `issued_at` is no more than 15 min old (and no more than 2 min in the future) and that the verdict is not NO_QUORUM.
- **Rationale**:
  - The constitution forbids server-side storage, and the server must not trust browser-edited votes, since those text fields reach a model.
  - Because the browser never parses and re-serialises the payload, float and date formatting differences between Python and JavaScript cannot break verification.
- **Alternatives**:
  - Browser re-sends the parsed result for the server to re-sign: breaks on JSON number round-trips.
  - Server-side cache keyed by an id: violates the no-storage rule and fails across Cloud Run instances.
  - JWT library: a new dependency for what 15 lines of standard library already do.
- **Notes**:
  - The payload is signed, not encrypted. It holds only what the browser already received in the vote result, so there is nothing secret in it.
  - Replay within 15 min is possible and harmless: the caller only gets another summary of their own vote, and the rate limit bounds it.

## D-303 — `QUORUM_SEAL_KEY` configuration

- **Decision**: A required env var (at least 32 bytes) for the summary feature. When it is missing:
  - the vote route omits `summary_token` (null);
  - the summary route answers 503;
  - the panel shows "Summary unavailable".

  `deploy_backend.sh` passes the var through like `LOG_PEPPER` and warns if it is unset.
- **Rationale**: All Cloud Run instances must share the key, and a key generated per process would fail across instances. Failing closed keeps the votes working.
- **Alternatives**: Reusing `LOG_PEPPER` was rejected because one key per purpose limits the blast radius and `LOG_PEPPER` has a weak default.

## D-304 — Figure catalog as the only source of displayed numbers

- **Decision**: New pure module `figure_catalog.py`. `build(ctx)` returns an ordered mapping `name → {label, value, display}` from the position context:
  - position-level figures: net delta (shares), net $ theta/day, net $ vega, max profit, max loss, % max profit captured, breakevens (`breakeven_1`, `breakeven_2`), minimum DTE;
  - per-leg figures, prefixed `leg{n}_`: strike, IV, RV, IV/RV, moneyness %, P(ITM), spot.

  `add_tally(catalog, verdict, tally, votes)` adds `votes_close`, `votes_hold`, `votes_roll`, `valid_votes`, `seats`, and `confidence_<seat_id>`. Unavailable figures (None) are left out, never zero-filled (018 FR-105). `display` uses one formatter per kind: `$1,234`, `38%`, `1.08×`, `+22 sh`, `12 d`, `$572.40`.
- **Rationale**: If every number on screen comes from the server's own values, the model can never invent a figure (spec clarification). Formatting matches the rest of the panel.
- **Alternatives**: Fuzzy matching of model-typed numbers against inputs was rejected in clarification. It is ambiguous around rounding and cannot tell a derived number from a correct one.

## D-305 — Summary route authentication

- **Decision**: Require and verify the Bearer token with Schwab (`verify_token`, as the vote route does) before unsealing.
- **Rationale**: Principle II requires authenticated endpoints. Without it, a leaked token could be replayed anonymously to spend Vertex quota. The check adds a few hundred ms inside a 15 s budget.
- **Alternatives**: Relying on the seal alone was rejected because it lets anyone holding a token string call the model within 15 minutes, with no auth.

## D-306 — Summariser agent shape

- **Decision**:
  - An ADK `LlmAgent`, `name="quorum_summariser"`, same model as the seats, `output_schema=SummaryDraft`, temperature 0.2, no tools, no transfers.
  - The instruction states: the verdict and tally are fixed facts; write figures only as `{name}` placeholders from the listed catalog; never write digits or number words; title ≤ 120 chars naming the verdict's action; explanation ≤ 3 sentences; 1–4 "why" bullets; one dissent paragraph ("No dissent" when unanimous); no forecast of what would change the call; not financial advice.
  - The user message wraps the payload in `DATA START`/`DATA END`, labelled untrusted, the same wording as the seat messages.
- **Rationale**: This reuses the seat pattern (`_run_agent`, `output_schema`), which is already covered by the fake-LLM tests.
- **Alternatives**: A raw `google.genai` call would mean a second code path with different retry and config behaviour.

## D-307 — Guard rules (server post-processing)

- **Decision**: Apply the following in order:
  1. Replace every `{name}` whose name is in the catalog with its `display` value.
  2. A text unit is *dirty* if, after step 1's replacements are set aside, it still contains an ASCII or Unicode digit, an unknown `{…}` placeholder, or a number word (zero–twenty, hundred, thousand, percent) that does not equal a tally count.
  3. If the title or explanation is dirty, discard the whole summary.
  4. Remove dirty "why" bullets. Split the dissent into sentences and remove the dirty ones. If no bullet remains, discard.
  5. Check the title for action words (close/closing/exit, hold/holding/keep, roll/rolling) and roll directions ("up and out", "down and out"). It must not name an action other than the verdict, nor a direction other than the direction shared by every ROLL voter (when they differ, no direction may be named). For NO_CONSENSUS it must not name close or roll.
  6. Truncate the fields to their limits, and keep only the first 3 sentences of the explanation.

  Log a discard or removal at INFO as `quorum summary guard outcome=<discarded|trimmed> reason=<code>`, with no text.
- **Rationale**: Deterministic, testable, and matches FR-309–FR-311. "Majority direction" (spec FR-310) is read as "the direction every ROLL voter shares". When they differ, only plain "roll" is allowed, which also sets the ring centre text.

## D-308 — Seat cited figures

- **Decision**: `AnalystBallot` gains `cited: list[str] = []` (at most 5, names only). The seat message appends a `FIGURES` list (name and label) after FUNDAMENTALS and asks the seat to list up to 5 names it relied on. The server maps names to `CitedFigure{name, label, display}` and drops unknown names and duplicates.
- **Rationale**: Chips show server values (FR-315), and the seats' existing rationale rules are unchanged (018 FR-115).

## D-309 — Ring rendering

- **Decision**: A pure `ringSvg(result, {animate})` in `quorum_ring.js` returns an SVG string:
  - five 72° wedges starting at 12 o'clock, 3° gaps, inner radius 50, outer radius 104 in a 460×280 viewBox (wide enough for side labels such as "ROLL down & out 70%"); the dashed ring at 50% confidence has no text label, because it collided with the top wedge's label;
  - fill radius = inner + (outer − inner) × confidence;
  - a 4-unit outer band in the vote colour;
  - CLOSE fill uses an SVG `<pattern>` hatch;
  - labels at radius 128, 11 px short name and 10 px vote and percentage;
  - each wedge `<g>` has `tabindex="0"`, `role="button"` and an `aria-label`.

  The palette constants are exported so rows, tally and badge share them.
- **Rationale**: Inline SVG needs no library, matches the existing `payoff_graph.js` approach, is CSP-safe (no inline script), and can be tested by string inspection in Node.

## D-310 — Button placement and panel width

- **Decision**: `quorumButtonCell()` becomes `adviceButton(id)`, which returns an inline `<button>` placed in the first `<td>` after the name. The name gets `max-width` with an ellipsis so the button never wraps off. The panel row keeps `colspan` for the table, and its inner wrapper is `position: sticky; left: 0` with its width set to the table container's `clientWidth` (updated on resize), so at 360 px it stays in view while the table scrolls sideways. Clicks call `stopPropagation()` so the spread toggle and graph handlers never see them (FR-303).
- **Rationale**: This is the approach proven in the mock. No change to the table's scroll model.

## D-311 — Client summary request lifecycle

- **Decision**: After rendering the vote result:
  - if the verdict is NO_QUORUM, show the fixed text and send nothing;
  - else if `summary_token` is null, show "Summary unavailable";
  - else show "Writing summary…" and `fetchWithAuth('/api/quorum/summary', {token})` with a client `AbortController` timeout of 20 s.

  The response is ignored if the panel was closed or replaced (the `_openId` check, as today). Any non-200, a `status: "unavailable"` response or an abort shows "Summary unavailable". The token is held only in a closure, never in the DOM or storage.
- **Rationale**: FR-306, FR-312, FR-313, and 017 FR-015.

## D-312 — Demo mode summary

- **Decision**: Demo mode keeps the live client code path. `demo_data.js` already intercepts `fetch('/api/quorum/vote')`; it now also intercepts `/api/quorum/summary`.
  - `buildDemoQuorum()` builds a catalog with the same names from the demo figures it already computes and assigns each demo seat's cited names. When the verdict is not NO_QUORUM, it sets `summary_token` to `"demo." + base64url(JSON payload)`. The payload is unsigned; it never leaves the browser.
  - The summary intercept decodes that payload and calls `buildDemoSummary(payload)`, which composes title, explanation, "why" and dissent from templates keyed by verdict (majority or NO_CONSENSUS) using `{name}` placeholders. The placeholders are filled with the catalog `display` values, and the summary is labelled "demo".
  - A token without the `demo.` prefix is answered "unavailable".
- **Rationale**: FR-321. No network request; the pending → ok states behave as in live mode; one rendering path to test.
