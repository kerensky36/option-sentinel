# Feature Specification: Fundamentals-First Quorum

**Feature Branch**: `claude/quorum-members-option-greeks-hqkzrd` (spec directory `018-fundamentals-first-quorum`)

**Created**: 2026-09-27

**Status**: Draft

**Amends**: `specs/017-macro-quorum-agents/spec.md` — replaces FR-002, FR-003, FR-004, FR-009, FR-010, FR-011 and FR-012 of spec 017 as stated below. All other 017 requirements (FR-001, FR-005–FR-008, FR-013–FR-020) remain in force unchanged.

**Input**: User description: "Improve the quorum members: focus first on the option fundamentals like Greeks and vol, then overlay market news. Compute the fundamentals as part of the positions pull, not when the quorum button is pressed. The quorum may use the browser's position data — a vote based on tampered data can be ignored, but it must be accurate in good faith. Limit the news to speed things up."

## Clarifications

### Session 2026-09-27

- Q: Should the quorum judge a position mainly on macro news or on the option's own numbers? → A: Option fundamentals (Greeks, volatility, time decay, strikes) first; market news is an overlay that can confirm or challenge the fundamentals view.
- Q: Can the Greeks and implied volatility come from Schwab, or must they be calculated? → A: Greeks and implied volatility come from Schwab's option chain (with the existing Black-Scholes fallback when missing). Volatility history, realised volatility, and all position-level figures (net Greeks, breakevens, expected move, etc.) are calculated by the app.
- Q: Must the server re-fetch the position from Schwab when the quorum is requested? → A: No. The browser sends the position and fundamentals it already holds from the last positions refresh. The trader accepts that tampered input yields a meaningless vote; the app must still be accurate in good faith (fresh data, strictly validated, no identifying data).
- Q: Does this need a constitution change? → A: No. Client data is held in sessionStorage as the constitution already requires, and the server keeps nothing between requests.
- Q: How much news? → A: At most 12 headlines (up to 5 reserved for the position's own ticker), only from the last 48 hours, and only the news-overlay analyst reads them.
- Q (plan refinement): Which fundamentals does the browser send? → A: Only realised volatility; the server re-derives the other leg fundamentals from the leg fields with the same code, so figures cannot drift from the legs and fewer values need validating.
- Q (plan refinement): Do the fundamentals seats see the research summary? → A: No. They start immediately and judge the numbers alone; the summary and headlines go only to the Macro & News Overlay seat, which is the seat that weighs events such as earnings before expiry.
- Q: Should the new fundamentals be displayed on the dashboard rows? → A: Out of scope for this feature (possible follow-up). They are fetched with positions and used by the quorum only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Quorum Judges the Option on Its Numbers First (Priority: P1) 🎯 MVP

A trader clicks Quorum on an option position or spread. Four of the five analysts judge the position on its own fundamentals — exposure (Greeks), volatility and pricing, time decay and profit captured, and strike/assignment risk — using figures the app has already calculated. The fifth analyst reads current market news and the macro research summary and says whether the news changes the picture. Each analyst's card cites the specific figure or headline behind its vote.

**Why this priority**: This is the core ask: votes that reflect how the option itself is behaving, rather than four variations of a macro opinion.

**Independent Test**: With the quorum configured, click Quorum on a short put that has captured 80% of its maximum profit with 5 days to expiry; verify five cards appear with the lenses Greeks & Exposure, Volatility & Pricing, Time Decay & P&L, Strike & Assignment, and Macro & News Overlay, and that the four fundamentals cards cite position figures (e.g. "80% of max profit captured") rather than headlines.

**Acceptance Scenarios**:

1. **Given** a completed quorum, **When** the panel renders, **Then** the five analyst cards show the lenses Greeks & Exposure, Volatility & Pricing, Time Decay & P&L, Strike & Assignment, and Macro & News Overlay.
2. **Given** a quorum request, **When** the four fundamentals analysts vote, **Then** each has been given the position's calculated fundamentals, but no headlines and no research summary.
3. **Given** a quorum request, **When** the news-overlay analyst votes, **Then** it has been given the position's fundamentals, the headlines, and the macro research summary.
4. **Given** a grouped spread, **When** the trader clicks Quorum on the spread summary row, **Then** the fundamentals describe the spread as a whole (net Greeks, combined breakevens, combined maximum profit), not each leg separately.
5. **Given** a figure the app could not calculate (e.g. realised volatility unavailable), **When** analysts vote, **Then** that figure is marked unavailable to them rather than guessed, and they vote on the rest.

---

### User Story 2 - Faster Quorum Using Data Already on Screen (Priority: P1)

The trader's positions refresh already gathers everything the fundamentals analysts need. Pressing Quorum sends that data straight to the analysts instead of pulling the whole position again from Schwab, and the news gathering, research, and fundamentals votes all happen at the same time. The panel shows when the underlying data was fetched ("Data as of 10:42").

**Why this priority**: Speed is a direct user request, and it makes the quorum practical to use on several positions in a row.

**Independent Test**: Refresh positions, click Quorum; verify the result shows the data timestamp matching the last refresh, and that no positions or option-chain request is made to Schwab during the quorum request.

**Acceptance Scenarios**:

1. **Given** positions refreshed 3 minutes ago, **When** the trader clicks Quorum, **Then** the quorum runs on that data and the panel shows "Data as of" the refresh time.
2. **Given** positions last refreshed more than 15 minutes ago, **When** the trader clicks Quorum, **Then** the request is rejected as stale and the panel asks the trader to refresh positions first.
3. **Given** a quorum request, **When** it runs, **Then** it makes at most one lightweight Schwab call (to confirm the trader's login is valid) and no positions, option-chain, or price-history calls.
4. **Given** an invalid or expired login token, **When** the trader clicks Quorum, **Then** the request is rejected as unauthorised before any model call is made.
5. **Given** a request containing any field other than the permitted position and fundamentals fields, or a value outside its allowed range, **When** it reaches the server, **Then** it is rejected as invalid input and no model call is made.

---

### User Story 3 - Honest Volatility Figures in Quorum and Screener (Priority: P2)

Wherever the app says whether volatility is "rich" or "cheap", it compares the option's implied volatility with the underlying's recent realised volatility, rather than a made-up rank. The covered-call screener shows this IV-to-realised-vol comparison in place of its current "IV Rank" figure, and the quorum's Volatility & Pricing analyst uses the same comparison.

**Why this priority**: The current screener "IV Rank" is a fixed multiple of implied volatility (any stock at 50% IV scores 100), which misleads both the trader and the analysts.

**Independent Test**: For an underlying whose implied volatility is 30% and whose realised volatility over the look-back window is 20%, verify the screener and the quorum both report IV at 1.5× realised volatility.

**Acceptance Scenarios**:

1. **Given** a covered-call screener row, **When** it renders, **Then** it shows implied volatility relative to realised volatility instead of "IV Rank".
2. **Given** realised volatility cannot be calculated for an underlying (e.g. price history unavailable), **When** the screener or quorum uses it, **Then** it is shown or passed as unavailable, never as zero.
3. **Given** the screener's recommendation score, **When** it is computed, **Then** its volatility component is based on the IV-to-realised-vol comparison.

---

### User Story 4 - Greeks Are Trustworthy (Priority: P2)

When Schwab returns a placeholder value for a Greek or implied volatility (such as -999 or "not a number") on an illiquid contract, the app treats it as missing and falls back to its own calculation instead of passing the placeholder on. A Greek that is genuinely zero (e.g. gamma on a deep in-the-money option) is kept as zero, not treated as missing.

**Why this priority**: Every fundamentals analyst depends on these numbers; one placeholder can distort the whole vote.

**Independent Test**: Feed a Schwab option-chain response with delta = -999 and gamma = 0 for a contract; verify delta is recalculated and marked "calculated", and gamma stays 0 marked "api".

**Acceptance Scenarios**:

1. **Given** Schwab returns -999, NaN, or another out-of-range placeholder for a Greek or implied volatility, **When** positions are refreshed, **Then** the value is treated as missing and the calculated fallback is used and labelled "calculated".
2. **Given** Schwab returns exactly 0 for a Greek, **When** positions are refreshed, **Then** 0 is kept and labelled as from Schwab.

---

### User Story 5 - Faster Positions Refresh (Priority: P3)

A positions refresh asks Schwab only for the option contracts the trader actually holds — their expiries and strikes — rather than the entire option chain for every underlying.

**Why this priority**: The full chain for heavily traded underlyings (e.g. SPY, QQQ) is very large and slows every refresh; it also offsets the added price-history lookup.

**Independent Test**: Refresh positions for an account holding one SPY option; verify the option-chain request is limited to that contract's expiry and strike and that the returned Greeks are unchanged from a full-chain fetch.

**Acceptance Scenarios**:

1. **Given** an account holding options on an underlying, **When** positions are refreshed, **Then** the option-chain request for that underlying is limited to the held contracts' expiry dates and strike range.
2. **Given** the narrowed request, **When** positions render, **Then** every held contract still has its Greeks and implied volatility.

---

### Edge Cases

- Realised volatility cannot be calculated (new listing, price history unavailable or too short): the figure is unavailable; IV-to-realised comparison is unavailable; everything else proceeds.
- The underlying price is unavailable: moneyness, breakevens relative to price, expected move, and probability of finishing in the money are unavailable; the analysts are told so.
- Days to expiry is 0 (expiration day): every time-based figure (expected move, probability of finishing in the money) uses a minimum of one day to expiry rather than dividing by zero; no figure is dropped because of expiry alone.
- A spread whose maximum profit or loss is undefined (e.g. a net-long call with unlimited upside): percent of maximum profit captured is unavailable; other figures proceed.
- The browser's position data is older than 15 minutes: rejected as stale; the panel asks the trader to refresh.
- The request carries values that are internally inconsistent (e.g. a modified mark): the quorum runs on them as given; the result reflects that input. Only shape and range are validated (tampering is the sender's problem, per clarification).
- Demo mode: the canned result uses the new five lenses and includes a "Data as of" timestamp; no server request is made (017 FR-018 unchanged).
- Headline feeds return only items older than 48 hours: the overlay analyst is told no recent headlines were found and relies on the research summary.
- The research step fails: the overlay analyst votes on headlines alone (017 behaviour preserved); the fundamentals analysts are unaffected because they never receive the summary.
- All other 017 edge cases (not configured, rate limit, timeout, prompt injection, one open panel at a time) are unchanged — except "symbol no longer in the account", which no longer applies because the server does not re-fetch the account; the stale-data rule covers it instead.

## Requirements *(mandatory)*

### Functional Requirements

#### Fundamentals (computed at positions refresh)

- **FR-101**: Each positions refresh MUST calculate, for every option leg, alongside the existing Greeks: the underlying's realised volatility over a fixed look-back window, implied volatility relative to that realised volatility, moneyness (percent distance of strike from the underlying price, signed in/out of the money), the expected move of the underlying to expiry implied by the option's volatility, the probability of finishing in the money, and the leg's dollar Greeks (Greek × signed quantity × contract multiplier).
- **FR-102**: Realised volatility MUST be calculated from the underlying's daily closing prices obtained from Schwab once per underlying per refresh (not once per leg), annualised. The look-back window defaults to 30 trading days.
- **FR-103**: Each positions refresh MUST record the time the data was fetched (the "as of" time) and return it with the positions.
- **FR-104**: When a quorum is requested, the server MUST calculate position-level fundamentals from the legs it receives: net and dollar Greeks for the whole position, breakeven price(s) at expiry, maximum profit and maximum loss where defined, percent of maximum profit captured, and daily time decay as a percent of the premium remaining. These are deterministic calculations, never model output.
- **FR-105**: Any fundamental that cannot be calculated from the available inputs MUST be marked unavailable, never substituted with zero or a guess.

#### Greeks quality

- **FR-106**: A Greek or implied volatility value from Schwab that is missing, not a number, infinite, or outside its valid range (including placeholder values such as -999) MUST be treated as missing, so the existing calculated fallback applies and is labelled "calculated".
- **FR-107**: A Greek value of exactly zero from Schwab MUST be kept and labelled as from Schwab; it MUST NOT trigger the calculated fallback.
- **FR-108**: The option-chain request made during a positions refresh MUST be limited to the expiry dates and strike range of the contracts held for that underlying.

#### Screener volatility

- **FR-109**: The covered-call screener MUST replace its "IV Rank" figure with implied volatility relative to the underlying's realised volatility (FR-102 method), and its recommendation score's volatility component MUST be derived from that comparison. When realised volatility is unavailable, or the row has no recommended call to take implied volatility from (suppressed or insufficient-data rows), the figure is shown as unavailable and the volatility component contributes nothing.

#### Quorum request (replaces 017 FR-002, FR-003)

- **FR-110** *(replaces 017 FR-002)*: Requesting a quorum MUST send the position's legs, as held by the browser from the last positions refresh, together with the one fundamental that cannot be derived from the leg fields (the underlying's realised volatility) and that refresh's "as of" time. The server MUST re-derive every other FR-101 leg fundamental from the received leg fields using the same calculation as the refresh, so the analysts see figures consistent with the legs. The server MUST NOT re-fetch the position, option chain, or price history from Schwab for a quorum request. The server MUST confirm the caller's login token is valid with a single lightweight Schwab request before any model call. The account identifier MUST NOT be sent.
- **FR-111** *(replaces 017 FR-003)*: The server MUST reject as invalid input any quorum request that: has zero or more than four legs; has legs on more than one underlying; contains any field not on the FR-113 list; contains a value outside its permitted type or range (numbers bounded to plausible market ranges, dates bounded, option type and seat-facing enumerations fixed, underlying symbol matching a ticker pattern of at most 10 uppercase letters, digits, dots, hyphens, slashes, carets or a leading dollar sign); or whose "as of" time is more than 15 minutes old or in the future beyond a small clock-skew allowance (rejected as stale).
- **FR-112**: The quorum result MUST include the "as of" time of the data it was based on, and the panel MUST show it ("Data as of HH:MM").

#### Data sent to the model (replaces 017 FR-011)

- **FR-113** *(replaces 017 FR-011)*: The data sent to Vertex AI MUST be limited to: underlying symbol, option type, strike, expiry, days to expiry, signed quantity, cost basis per contract, current mark, unrealised P&L, Greeks, implied volatility, underlying price, the FR-101 per-leg fundamentals, the FR-104 position-level fundamentals, the data "as of" time, and — for the news-overlay analyst only — the macro research summary and the gathered headlines. User-identifiable or pedigree data (Constitution v3.3.0, Principle I) MUST NOT be sent — including names, emails, addresses, phone numbers, dates of birth, government/tax IDs, account numbers, account hashes, tokens, and IP addresses. Free-text fields supplied by the browser MUST NOT be accepted.

#### Analyst seats (replaces 017 FR-004)

- **FR-114** *(replaces 017 FR-004)*: The quorum MUST consist of exactly five independent analyst seats with these fixed lenses:
  1. **Greeks & Exposure** — net and dollar delta, gamma, vega; directional and gamma risk, especially near expiry.
  2. **Volatility & Pricing** — implied volatility versus realised volatility, whether the option is rich or cheap, expected move versus breakevens.
  3. **Time Decay & P&L** — time decay, days to expiry, percent of maximum profit captured, remaining reward versus remaining risk.
  4. **Strike & Assignment** — moneyness, probability of finishing in the money, early-assignment and pin risk.
  5. **Macro & News Overlay** — the only seat given headlines; judges whether current news and the macro backdrop confirm or override the fundamentals picture.
- **FR-115**: Seats 1–4 MUST form their vote primarily from the position fundamentals and cite at least one specific figure in their rationale. Seat 5 MUST cite a specific headline or research point, or state that the news was thin.

#### News and research (replaces 017 FR-009, FR-010, FR-012)

- **FR-116** *(replaces 017 FR-009)*: News MUST be gathered at request time from the same CNBC, Yahoo Finance, and Bloomberg public feeds plus the Yahoo Finance feed for the position's underlying. Only headlines published within the last 48 hours are kept (headlines with no publication time are dropped). After de-duplication by title, at most 12 headlines are passed to the news-overlay analyst and returned in the result: up to 5 from the underlying's own feed (newest first), with the remaining places filled by the newest general headlines.
- **FR-117** *(replaces 017 FR-010)*: A research agent MUST summarise, using Google Search grounding focused on the same three publishers, news and scheduled events relevant to the position's underlying before the position's expiry (e.g. earnings, ex-dividend dates, scheduled economic releases), plus a brief note on the macro backdrop. Its summary is given read-only to seat 5 (Macro & News Overlay) only. If research fails, seat 5 proceeds on headlines alone.
- **FR-118** *(replaces 017 FR-012)*: The whole quorum MUST complete or fail within 60 seconds; individual feed fetches MUST time out after 3 seconds.
- **FR-119**: The news gathering, the research agent, and seats 1–4 MUST start at the same time; only seat 5 waits for the headlines and research summary. Seats 1–4 never wait on news or research.

#### Disclosure

- **FR-120**: The "How we use your data" page (017 FR-019) MUST be updated so the Vertex AI row lists the FR-113 fields, and a row MUST state that daily closing prices for held underlyings are fetched from Schwab to calculate realised volatility.

### Key Entities

- **Leg Fundamentals**: Per-leg calculated figures attached to each position at refresh time — realised volatility of the underlying, IV relative to realised volatility, moneyness, expected move to expiry, probability of finishing in the money, dollar Greeks — each possibly unavailable.
- **Position Fundamentals**: Position-level figures calculated at quorum time from the legs — net and dollar Greeks, breakevens, maximum profit and loss where defined, percent of maximum profit captured, daily time decay as percent of remaining premium.
- **Quorum Request**: The legs (FR-113 leg fields plus realised volatility) and the data "as of" time; no account identifier and no leg symbol.
- **Quorum Result** *(extends 017)*: Adds the data "as of" time and the position fundamentals the analysts were given; seats use the FR-114 lenses; headlines are the at-most-12 given to the overlay seat.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-101**: For the same position with all news feeds responding, the median time-to-verdict over 5 consecutive runs is at least 5 seconds lower than the spec 017 build's median over 5 runs; no run exceeds 60 seconds.
- **SC-102**: A quorum request makes no positions, option-chain, or price-history request to Schwab (verified by automated test).
- **SC-103**: For a representative set of single-leg and spread positions, every calculated fundamental matches an independent reference calculation to within 1% (or is correctly marked unavailable).
- **SC-104**: 100% of placeholder Greek values (-999, NaN, infinite, out of range) in test fixtures are replaced by calculated values, and 100% of genuine zero values are preserved.
- **SC-105**: In a review of at least 10 quorum results, every card from seats 1–4 cites a specific position figure, and seat 5 is the only card citing headlines.
- **SC-106**: 100% of quorum requests carrying an extra field, an out-of-range value, or data older than 15 minutes are rejected before any model call (verified by automated test).
- **SC-107**: No user-identifiable or pedigree data appears in any model request (017 SC-003, re-verified against the new request shape).
- **SC-108**: A positions refresh requests option-chain data only for the held contracts' expiry range (and single strike when only one strike is held), and returns Greeks identical to a full-chain fetch for every held contract (verified by automated test).

## Assumptions

- The quorum remains advisory and never places a trade (Constitution V; 017 FR-017).
- No constitution change is required: client position data (now including fundamentals) stays in sessionStorage; the server processes it within one request and retains nothing.
- The trader accepts that a quorum run on tampered browser data is meaningless; validation guarantees only shape, range, freshness, and the privacy allow-list — not that the numbers match Schwab.
- Probability of finishing in the money uses the standard Black-Scholes risk-neutral estimate with the option's implied volatility and the app's configured risk-free rate.
- Expected move to expiry is underlying price × implied volatility × √(days to expiry / 365).
- Realised volatility uses 30 trading days of daily closes, annualised with 252 trading days; the window is a configurable default.
- The extra price-history request (one per held underlying per refresh) stays well within Schwab's API rate limits for a personal portfolio, and is offset by the narrower option-chain request.
- True IV rank/percentile (requiring stored IV history) is out of scope; IV relative to realised volatility is the volatility signal.
- Displaying the new fundamentals on dashboard rows is out of scope (possible follow-up feature).
- User Stories 1 and 2 share the quorum code path; Story 2 builds on Story 1's seat changes, and the two ship together as the minimum viable release.
- The tally rule, abstention handling, ballot shape, rate limit, result panel layout, demo mode, and disclosure page mechanics are unchanged from spec 017.
