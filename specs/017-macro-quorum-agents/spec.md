# Feature Specification: Macro News Voting Quorum

**Feature Branch**: `claude/google-adk-options-quorum-jaeq8f` (spec directory `017-macro-quorum-agents`)
**Created**: 2026-09-25
**Status**: Draft
**Input**: User description: "Add Google ADK agents to build a voting quorum on whether to buy, hold, roll an existing options position based on macro data"

## Clarifications

### Session 2026-09-25

- Q: For an existing options position, what does the "buy" vote mean? → A: Buy (or sell) to close. The three possible votes are **CLOSE**, **HOLD**, **ROLL**.
- Q: How do the agents reach the language model? → A: Google Vertex AI (Gemini) in the operator's own GCP project, authenticated by the Cloud Run service account — no API key stored anywhere.
- Q: Where does the macro data come from? → A: Financial news sources — CNBC, Yahoo Finance, Bloomberg — rather than a statistics API.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask the Quorum About One Position (Priority: P1) 🎯 MVP

A trader looking at an open option position (single leg or a grouped spread) on the dashboard clicks a **Quorum** button on that row. A panel opens under the row and, within about a minute, shows a single verdict — **CLOSE**, **HOLD**, **ROLL**, or **NO CONSENSUS** — along with the vote tally (e.g. "ROLL 3 · HOLD 1 · CLOSE 1") produced by a panel of independent AI analysts who each read the current macro news and the position's details.

**Why this priority**: This is the whole feature. A single, glanceable verdict backed by a visible majority is what the trader asked for.

**Independent Test**: With the quorum configured, click Quorum on any option row; verify a verdict and a tally with five seats appear, and that the verdict equals the action holding a strict majority (or NO CONSENSUS when none does).

**Acceptance Scenarios**:

1. **Given** an authenticated trader with an open option position, **When** they click the row's Quorum button, **Then** a panel opens beneath the row showing a loading state, followed by a verdict and a five-seat tally.
2. **Given** the five analysts return votes of ROLL, ROLL, ROLL, HOLD, CLOSE, **When** the result renders, **Then** the verdict is ROLL (3 of 5, a strict majority).
3. **Given** the five analysts return votes of ROLL, ROLL, HOLD, HOLD, CLOSE, **When** the result renders, **Then** the verdict is NO CONSENSUS and the panel states that no action reached a majority (status quo is to hold).
4. **Given** only two of the five analysts return a usable vote (others time out or return malformed output), **When** the result renders, **Then** the verdict is NO QUORUM and no action is recommended.
5. **Given** a grouped spread row, **When** the trader clicks Quorum on the spread's summary row, **Then** the quorum evaluates the spread as one position (all legs together), not each leg separately.

---

### User Story 2 - See Why Each Analyst Voted the Way They Did (Priority: P2)

Below the verdict, the trader sees one compact card per analyst: the analyst's lens (e.g. "Rates & Fed"), their vote, their confidence, a short rationale, and — for ROLL votes — the suggested roll direction. The trader also sees the list of news headlines (source, title, link) the analysts were given, so they can judge the evidence themselves.

**Why this priority**: A verdict with no reasons is not trustworthy for real money. This makes the quorum auditable, but Story 1 still delivers value without it.

**Independent Test**: Open a quorum result; verify five analyst cards with lens, vote, confidence and rationale, and a headline list where each item shows its publisher and opens the original article in a new tab.

**Acceptance Scenarios**:

1. **Given** a completed quorum, **When** the panel renders, **Then** each seated analyst appears with lens name, vote, confidence (0–100%), and rationale.
2. **Given** an analyst voted ROLL, **When** their card renders, **Then** it shows the suggested roll direction (out, up-and-out, or down-and-out).
3. **Given** the news gathered for the vote, **When** the panel renders, **Then** every headline shows its publisher (CNBC / Yahoo Finance / Bloomberg) and title, linked to the original article, opening in a new tab.
4. **Given** an analyst failed to return a usable vote, **When** the panel renders, **Then** that seat is shown as "abstained" rather than hidden.

---

### User Story 3 - Try the Quorum in Demo Mode (Priority: P3)

A visitor using demo mode (specs/014) clicks Quorum on a demo position and sees a realistic, canned quorum result, without any Schwab connection or model call.

**Why this priority**: Keeps demo mode representative of the full product; no live value.

**Independent Test**: Enter demo mode, click Quorum on any demo row, verify a complete result renders with no network request to the quorum endpoint.

**Acceptance Scenarios**:

1. **Given** demo mode, **When** the visitor clicks Quorum on any row, **Then** a complete canned result (verdict, tally, analyst cards, headlines) renders and no request reaches the server.

---

### Edge Cases

- The quorum is not configured on the server (no GCP project set): the endpoint answers "service unavailable" with a plain message; the panel shows "Quorum is not configured on this server" and nothing else breaks.
- News feeds are unreachable or return nothing: the quorum still runs using the position's own data and whatever news was gathered; the headline list says "No headlines could be retrieved" and the analysts are told news was unavailable.
- One publisher's feed fails but others succeed: headlines from the working publishers are used; the failure is silent to the user.
- The whole quorum exceeds its time budget (60 s): the endpoint returns "gateway timeout"; the panel shows a retryable error.
- The trader clicks Quorum on a symbol that is no longer in their account (closed since the last refresh): the endpoint answers "not found"; the panel asks the trader to refresh positions.
- Selected legs span more than one underlying: rejected as invalid input.
- A news headline contains text trying to instruct the analysts (prompt injection): analysts can only emit one of three enumerated actions plus bounded text; nothing an analyst writes can trigger any action, and every string is escaped when rendered.
- Clicking Quorum on a second row while a panel is open closes the first panel (one open panel at a time, matching payoff graph behavior). Clicking the same row's Quorum button again closes it.
- Clicking the Quorum button MUST NOT also open or close the payoff graph for that row.
- Rate limit reached (quorums are expensive): the endpoint answers "too many requests"; the panel shows a "try again in a minute" message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every standalone option row and every spread summary row on the positions dashboard MUST offer a Quorum button.
- **FR-002**: Requesting a quorum MUST send only the position's leg symbols and the selected account identifier to the server; the server MUST re-fetch the position from Schwab using the caller's own token and MUST NOT trust any client-supplied prices, Greeks, or quantities.
- **FR-003**: The server MUST reject a request whose symbols are not all present in the caller's selected account (not found), whose account identifier is not on the caller's token (invalid input, per existing account-hash validation), that names zero or more than four legs, or whose legs span more than one underlying (invalid input).
- **FR-004**: The quorum MUST consist of exactly five independent analyst seats, each with a distinct, fixed lens: (1) Rates & Fed policy, (2) Volatility regime, (3) Growth & Inflation, (4) Underlying & Sector news, (5) Position Risk (Greeks, days to expiry, P&L).
- **FR-005**: Each analyst MUST return exactly one vote from the set {CLOSE, HOLD, ROLL}, a confidence between 0 and 1, and a rationale (truncated to 600 characters); a ROLL vote MUST include a roll direction from {out, up_and_out, down_and_out}. Any output that does not satisfy this shape, errors, or exceeds its time budget MUST be counted as an abstention and MUST NOT prevent the other seats from voting.
- **FR-006**: Analysts MUST run independently — no analyst sees another analyst's vote before voting.
- **FR-007**: The tally MUST be computed deterministically by the server, not by a model: quorum is met when at least 3 of 5 seats cast a valid vote; the verdict is the action with at least 3 votes (a strict majority of the five seats); if quorum is met but no action has 3 votes the verdict is NO_CONSENSUS; if quorum is not met the verdict is NO_QUORUM.
- **FR-008**: The result MUST include, per action, the vote count and the mean confidence of the analysts who chose it.
- **FR-009**: Macro news MUST be gathered at request time from CNBC, Yahoo Finance, and Bloomberg public news feeds, plus the Yahoo Finance headline feed for the position's underlying symbol; at most 30 headlines, de-duplicated by title, newest first, are passed to the analysts and returned in the result.
- **FR-010**: A news-research agent MUST additionally summarise current macro conditions for the analysts using Google Search grounding focused on the same three publishers; its summary is shared read-only with all five analysts. If research fails, analysts proceed with headlines only.
- **FR-011**: The data sent to the model MUST be limited to public-market and contract-level fields: underlying symbol, option type, strike, expiry, days to expiry, signed quantity, cost basis per contract, current mark, unrealised P&L, Greeks, implied volatility, underlying price, and the gathered headlines. Account identifiers, tokens, and any other account data MUST NOT be sent.
- **FR-012**: The whole quorum (news + research + votes) MUST complete or fail within 60 seconds; individual feed fetches MUST time out after 5 seconds.
- **FR-013**: The quorum endpoint MUST be rate-limited more strictly than other endpoints (5 requests per minute per client).
- **FR-014**: If the server is not configured for the quorum, the endpoint MUST answer "service unavailable" without attempting any model call.
- **FR-015**: The quorum result MUST NOT be persisted anywhere — not on the server, and not in browser storage; closing the panel discards it.
- **FR-016**: The result panel MUST show the verdict, tally, per-analyst cards (FR-005 fields, abstentions marked), and the headline list with publisher and link; all text MUST be escaped; links MUST open in a new tab with no opener/referrer.
- **FR-017**: The result MUST display a fixed notice that it is informational only and not financial advice; no trade is ever placed by this feature.
- **FR-018**: In demo mode, the Quorum button MUST return a canned result client-side without contacting the server.

### Key Entities

- **Position Context**: The de-identified description of one position (one or more legs sharing an underlying) that the analysts evaluate — see FR-011 for the exact field list.
- **Headline**: A news item: publisher, title, link, published time, short summary.
- **Analyst Vote**: Seat name, lens, action (CLOSE/HOLD/ROLL) or abstention, confidence, rationale, roll direction.
- **Quorum Result**: Verdict (CLOSE / HOLD / ROLL / NO_CONSENSUS / NO_QUORUM), per-action tally, the five analyst votes, the macro research summary, the headlines used, the model name, and a generated-at timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A trader gets a verdict for any open position with one click and without leaving the dashboard, in under 60 seconds.
- **SC-002**: For any combination of five votes, the displayed verdict matches the FR-007 rule in 100% of cases (verified by exhaustive automated test over all 4⁵ vote/abstain combinations).
- **SC-003**: No account identifier or token value ever appears in any text sent to the model (verified by automated test of the prompt payload).
- **SC-004**: Every analyst's reasoning and every headline behind a verdict is visible to the trader from the same panel.
- **SC-005**: The feature degrades without breaking the dashboard in every edge case listed above.

## Assumptions

- Vertex AI in the operator's own GCP project (the one that already hosts Cloud Run) is the model provider; data sent there is governed by the operator's GCP terms and is not used for model training. This conflicts with Constitution Principle I (v3.2.0); proceeding requires the user to approve an amendment (see research D-008) — not yet approved.
- Public RSS feeds from CNBC, Yahoo Finance, and Bloomberg are used as "news sources"; paywalled article bodies are not fetched — only headline, summary, and link.
- The default model is a fast Gemini model configurable by environment variable, so the operator can move to newer models without a code change.
- "Roll" suggestions are directional only (out / up-and-out / down-and-out); choosing concrete strikes and expiries remains the trader's job.
- The verdict is advisory. Option Sentinel remains position-retrieval only; no order is ever placed (Constitution V, Technology Constraints).
