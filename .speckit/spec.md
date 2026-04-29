# Feature Specification: Option Sentinel

**Feature Branch**: `001-option-sentinel-monitor`  
**Created**: 2026-04-28  
**Status**: Draft  
**Input**: User description: "Personal options position monitor that connects to the Schwab API, automatically tracks open positions, fires alerts when pre-defined trading rules trigger, and displays a live dashboard."

## Clarifications

### Session 2026-04-29

- Q: Is a thesis per-position or a grouping entity for multiple positions? → A: Template-based thesis groups — theses are named, template-defined entities; multiple positions are assigned to one thesis group rather than each position holding its own thesis.
- Q: Where do Greeks come from — Schwab API, third-party, or calculated? → A: Schwab API first; fallback to Black-Scholes calculation for any Greek not returned by Schwab; source tracked per-field (api | calculated | unavailable).
- Q: How is thesis alignment scored — qualitative, numeric, or composite? → A: Composite — automatic exit proximity score (0–100) plus manual thesis alignment rating; shown as two separate signals per position.
- Q: What constitutes an exit goal — P&L %, DTE, price target, or all three? → A: All three — P&L % target, DTE threshold, and underlying price target; any one reaching its threshold signals exit proximity.
- Q: Should scoring drive automated alerts or remain display-only? → A: Display only for initial delivery; no automated alerts from scoring.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Live Position Dashboard (Priority: P1)

A trader opens the Option Sentinel dashboard and immediately sees all of their current open options positions. Each position displays its current market value, unrealised P&L, days to expiry, Greeks, exit proximity score, and thesis group assignment. The data reflects the latest available market prices, refreshed automatically during trading hours.

**Why this priority**: Without a clear view of open positions, none of the alerting or management features have context. This is the foundational view the trader relies on throughout the trading day.

**Independent Test**: Can be tested by connecting to a brokerage account with at least one open position, opening the dashboard, and verifying that the position appears with accurate data fields including Greeks. Delivers standalone value as a position viewer even before any alert rules are active.

**Acceptance Scenarios**:

1. **Given** the trader has open options positions in their brokerage account, **When** they open the dashboard, **Then** all open positions are displayed with symbol, option type, strike, expiry date, quantity, current mark price, unrealised P&L, days to expiry, Greeks (delta, gamma, theta, vega, IV with source indicator), exit proximity score, and thesis group assignment.
2. **Given** the dashboard is open during market hours, **When** the data refresh interval elapses, **Then** position values and Greeks update to reflect current market prices without a manual page reload.
3. **Given** the market is closed, **When** the trader opens the dashboard, **Then** positions are still visible with the last known values and a clear indication that live prices are unavailable.
4. **Given** Schwab does not return a Greek value for a position, **When** the dashboard displays that position, **Then** the Greek is calculated via Black-Scholes and shown with a "calculated" indicator rather than a dash.

---

### User Story 2 - Credit Spread Profit Target Alert (Priority: P2)

When one of the trader's credit spread positions reaches 50% of its maximum possible profit, the system sends an alert prompting the trader to consider closing the position. The trader receives this notification via email so they can act promptly even when away from the dashboard.

**Why this priority**: The 50% profit target close is the trader's primary management rule. Missing this trigger can result in giving back gains, making reliable alerting critical to the trading strategy.

**Independent Test**: Can be tested by entering a credit spread position with a known maximum profit and adjusting its current mark to cross the 50% threshold; the system should generate and deliver an email alert.

**Acceptance Scenarios**:

1. **Given** an open credit spread position with a defined maximum profit, **When** the current mark-to-market value indicates 50% or more of that profit has been captured, **Then** the trader receives an email alert identifying the position, the current P&L percentage, and a suggested action to close.
2. **Given** the alert has already fired for a position in the current trigger event, **When** subsequent polls continue to show the threshold is met, **Then** the alert does not re-fire until the position has reset below the threshold and re-triggered.
3. **Given** the position is closed or has expired, **When** the next refresh occurs, **Then** no further profit-target alerts are generated for that position.

---

### User Story 3 - Expiry Warning Escalation (Priority: P2)

As an options position approaches its expiration date, the trader receives a series of escalating warnings: at 14 days out, at 7 days, and at 3 days. Each warning clearly states the position, expiry date, and which tier has been reached, helping the trader plan and act before time value decays further or the position expires worthless.

**Why this priority**: Time decay and assignment risk accelerate near expiry. Missing these windows can result in maximum loss. Escalating alerts give the trader structured decision points.

**Independent Test**: Can be tested by setting a position's expiry to 14 days away and confirming the first-tier alert fires; repeat for 7-day and 3-day thresholds independently.

**Acceptance Scenarios**:

1. **Given** an open position reaches 14 calendar days to expiry, **When** the daily expiry check runs, **Then** the trader receives a 14-day expiry warning email for that position.
2. **Given** an open position reaches 7 calendar days to expiry, **When** the daily expiry check runs, **Then** the trader receives a 7-day expiry warning email, distinct from the prior 14-day warning.
3. **Given** an open position reaches 3 calendar days to expiry, **When** the daily expiry check runs, **Then** the trader receives an urgent 3-day expiry warning email.
4. **Given** a warning tier has already been sent for a position, **When** subsequent checks occur while still at the same tier, **Then** the warning does not repeat.

---

### User Story 4 - Binary Event Exit Protocol (Priority: P2)

Before a major scheduled event (earnings, FOMC, etc.), the trader manually raises a "binary event" flag in the dashboard. This immediately triggers a full-exit alert covering every open position, prompting the trader to close all exposure before the event. The flag stays active and visible until the trader explicitly clears it.

**Why this priority**: Binary events can gap positions beyond recovery. A single-action full-portfolio exit prompt prevents the trader from missing any position during a high-stress, time-limited window.

**Independent Test**: Can be tested by setting the binary event flag with two or more open positions active; all positions should appear in a single consolidated exit alert email within one minute.

**Acceptance Scenarios**:

1. **Given** the trader raises the binary event flag, **When** the flag is saved, **Then** an immediate email alert is sent listing every open position with a clear instruction to close all positions.
2. **Given** the binary event flag is active, **When** the dashboard is opened, **Then** a prominent visual indicator shows the flag is in effect.
3. **Given** the flag is active and a new position is opened, **When** the next data refresh occurs, **Then** the new position is included in the active exit alert state and shown in the dashboard banner.
4. **Given** the trader clears the binary event flag, **When** the flag is removed, **Then** the dashboard returns to normal state and no further binary-event alerts fire.

---

### User Story 5 - Thesis Groups & Position Scoring (Priority: P3)

The trader creates named thesis groups using predefined templates (e.g., "IV crush play", "earnings fade", "directional momentum", "mean reversion", "custom") and assigns one or more open positions to each group. The dashboard groups positions by thesis and displays two scoring signals per position: an automatically computed exit proximity score and a manually set thesis alignment rating inherited from the group. This lets the trader instantly see which positions are on-track and which need attention.

**Why this priority**: Thesis grouping and scoring are qualitative risk management tools. They add decision context but do not drive automated alerts, making them lower priority than the core alerting rules.

**Independent Test**: Can be tested by creating a thesis group, assigning two positions to it, setting exit goals on each position, and confirming that exit proximity scores update on the next poll and that the thesis alignment rating is visible on both positions.

**Acceptance Scenarios**:

1. **Given** the trader creates a thesis group with a template type and name, **When** they assign one or more positions to it, **Then** those positions appear grouped under the thesis on the dashboard.
2. **Given** a thesis group exists, **When** the trader sets its alignment rating to "aligned", "partially aligned", or "misaligned", **Then** all positions in the group display that rating.
3. **Given** a position has at least one exit goal defined (P&L %, DTE, or price target), **When** a poll cycle completes, **Then** the position displays an exit proximity score (0–100) reflecting how close the nearest exit goal dimension is to its threshold.
4. **Given** a position belongs to no thesis group, **When** it is displayed on the dashboard, **Then** it appears in an "Unassigned" group with no alignment rating.
5. **Given** a position has no exit goals defined, **When** it is displayed on the dashboard, **Then** the exit proximity score shows "—" rather than 0.

---

### Edge Cases

- What happens when the brokerage account has no open positions? Dashboard shows an empty state with a clear message rather than an error.
- What happens when the access token expires mid-poll? System silently refreshes the token and retries the poll; the user sees no interruption.
- What happens when the refresh token expires (7-day window)? The system surfaces a prominent re-authentication prompt and pauses polling until the user re-authenticates.
- What happens when a position simultaneously triggers both a profit-target alert and a 3-day expiry alert? Both alerts are delivered independently.
- What happens when a position is partially closed at the brokerage? Position data reflects the current remaining quantity; alerts recalculate against the updated figures.
- What happens when the market is closed and the binary event flag is raised? The full-exit alert fires immediately regardless of market hours; polling suspension does not block this alert.
- What happens if email delivery fails? The alert is logged locally and retried on the next poll cycle up to 3 attempts before being marked failed.
- What happens when Schwab does not return any Greeks for a position and Black-Scholes cannot be computed (e.g., missing underlying price)? All Greek fields display "—" with an "unavailable" indicator; no error is surfaced to the trader.
- What happens when a thesis group is deleted? Positions previously in that group move to "Unassigned"; their exit goals and scores are preserved.

## Requirements *(mandatory)*

### Functional Requirements

**Position Tracking**

- **FR-001**: The system MUST connect to the trader's brokerage account and retrieve all open options positions automatically.
- **FR-002**: The system MUST refresh position data every 5 minutes while the market is open (US equity market hours: 9:30 AM – 4:00 PM ET, Monday–Friday, excluding US market holidays).
- **FR-003**: All position data MUST be stored locally and MUST NOT be transmitted to any external service other than the brokerage API.
- **FR-004**: The system MUST handle brokerage access token expiry transparently, refreshing tokens automatically without user intervention.
- **FR-005**: The system MUST detect when the brokerage refresh token is nearing its 7-day expiry and display a clear re-authentication prompt to the trader before polling is interrupted.

**Dashboard**

- **FR-006**: The dashboard MUST display all open positions with: underlying symbol, option type, strike, expiry date, quantity, current mark price, unrealised P&L, days to expiry, Greeks (delta, gamma, theta, vega, IV), exit proximity score, and thesis group assignment.
- **FR-007**: The dashboard MUST show when the last successful data refresh occurred and the current polling status.
- **FR-008**: The dashboard MUST display a visible banner or indicator when the binary event flag is active.
- **FR-009**: The dashboard MUST allow the trader to raise and clear the binary event flag.
- **FR-010**: The dashboard MUST group positions by thesis group and display an "Unassigned" group for positions not yet assigned to a thesis.

**Greeks**

- **FR-011**: The system MUST retrieve Greeks (delta, gamma, theta, vega, implied volatility) from the Schwab API for each open options position on every poll cycle.
- **FR-012**: For any Greek not returned by the Schwab API, the system MUST calculate an approximation using Black-Scholes, using the current underlying price, option mark price, strike, expiry date, and a configurable risk-free rate.
- **FR-013**: Each Greek value displayed on the dashboard MUST include a source indicator: `api`, `calculated`, or `unavailable`.

**Thesis Groups**

- **FR-014**: The system MUST allow the trader to create thesis groups using predefined templates: "IV crush play", "earnings fade", "directional momentum", "mean reversion", and "custom".
- **FR-015**: The trader MUST be able to assign one or more positions to a thesis group from the dashboard.
- **FR-016**: The trader MUST be able to set a thesis alignment rating (aligned | partially aligned | misaligned) at the thesis group level; all positions in the group inherit this rating.
- **FR-017**: Deleting a thesis group MUST move its positions to "Unassigned" without deleting the positions or their exit goals.

**Exit Goals & Scoring**

- **FR-018**: The trader MUST be able to define up to three exit goal dimensions per position: P&L % target, DTE threshold, and underlying price target (with direction: above or below).
- **FR-019**: The system MUST compute an exit proximity score (0–100) for each position on every poll cycle, reflecting the nearest exit goal dimension to its threshold. A score of 100 means at least one exit goal has been met.
- **FR-020**: Exit proximity scoring MUST be display-only; it MUST NOT trigger automated alerts.

**Alerting — Close Trigger**

- **FR-021**: The system MUST calculate the maximum profit for each credit spread based on the net credit received at open.
- **FR-022**: The system MUST fire an email alert when a credit spread position's mark indicates that 50% or more of its maximum profit has been captured.
- **FR-023**: The close-trigger alert MUST NOT repeat for the same position within the same trigger event; it re-arms only after the position drops below the threshold and re-crosses it.

**Alerting — Expiry Warnings**

- **FR-024**: The system MUST send an email alert when an open position reaches 14 calendar days to expiry.
- **FR-025**: The system MUST send an email alert when an open position reaches 7 calendar days to expiry.
- **FR-026**: The system MUST send an email alert when an open position reaches 3 calendar days to expiry.
- **FR-027**: Each expiry warning tier MUST fire only once per position per threshold crossing.

**Alerting — Binary Event Exit**

- **FR-028**: When the trader raises the binary event flag, the system MUST immediately send a single consolidated email listing all open positions with an instruction to exit all positions.
- **FR-029**: The binary event alert MUST fire once per flag-raise event; re-raising the flag after it has been cleared triggers a new alert.

**Alerting — Delivery**

- **FR-030**: The system MUST deliver alerts via email as the primary notification channel.
- **FR-031**: The system MUST log all alert events locally with timestamp, alert type, position reference, and delivery status.
- **FR-032**: Failed alert deliveries MUST be retried up to 3 times before being marked as permanently failed in the local log.

### Key Entities

- **Position**: A single open options leg or spread. Key attributes: underlying symbol, option type, strike, expiry date, quantity, opening credit/debit, current mark value, open/closed status, thesis group reference (nullable), exit goals reference.
- **Greeks**: Option sensitivity values attached to a Position. Key attributes: delta, gamma, theta, vega, implied_volatility — each with a source field (`api` | `calculated` | `unavailable`).
- **ExitGoal**: Exit targets for a Position. Key attributes: profit_target_pct (nullable), dte_threshold (nullable), underlying_price_target (nullable), price_target_direction (`above` | `below`, nullable), exit_proximity_score (computed 0–100).
- **Thesis**: A named grouping of positions sharing a market thesis. Key attributes: name, template_type (`iv_crush` | `earnings_fade` | `directional_momentum` | `mean_reversion` | `custom`), description, created_at, status (`active` | `closed`), alignment_rating (`aligned` | `partially_aligned` | `misaligned` | `unrated`).
- **Spread**: Groups related position legs into a named strategy (e.g., credit spread). Key attributes: strategy type, maximum profit, maximum loss, net credit received, member legs.
- **Alert**: A triggered notification event. Key attributes: alert type, position or spread reference, severity, trigger timestamp, delivery status, retry count, acknowledged timestamp.
- **AuthToken**: Brokerage OAuth token state. Key attributes: access token, access expiry, refresh token, refresh expiry, re-auth required flag.
- **BinaryEventFlag**: The trader's manual full-exit signal. Key attributes: active state, activated timestamp, cleared timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All open positions are visible on the dashboard within 10 minutes of being opened at the brokerage (at most two poll cycles).
- **SC-002**: Alert notifications are delivered within 5 minutes of the triggering condition being detected during a poll.
- **SC-003**: The binary event exit alert is delivered within 60 seconds of the trader raising the flag.
- **SC-004**: The trader can assign a position to a thesis group and define at least one exit goal in under 60 seconds from the dashboard.
- **SC-005**: The system operates continuously during market hours with zero unplanned polling interruptions caused by token expiry.
- **SC-006**: No position data is transmitted to any destination other than the brokerage API (verifiable by network inspection).
- **SC-007**: 100% of triggered alerts for the 3-day expiry threshold and the close-trigger rule result in a delivered or logged-retry notification.
- **SC-008**: The re-authentication prompt appears at least 24 hours before the refresh token expires.
- **SC-009**: Greek values (from API or calculated) are displayed for all open positions within one poll cycle of the dashboard opening.

## Assumptions

- The trader operates a single brokerage account; multi-account support is out of scope.
- "Market hours" means US equity market hours: 9:30 AM – 4:00 PM ET, Monday through Friday, excluding US market holidays. The holiday calendar is embedded in the application and updated annually.
- The trader's brokerage (Charles Schwab) provides a publicly accessible OAuth2 API supporting position retrieval. No internal or institutional API access is assumed.
- The Schwab API may return Greeks on option quote responses; availability is not guaranteed for all strikes/expiries. Black-Scholes fallback uses the US 3-month Treasury rate as the risk-free rate, configurable via environment variable.
- The net credit received for each spread is either returned by the brokerage API as cost-basis data or entered manually by the trader at position open, as the API may not expose this value in a directly usable format.
- Expiry warning thresholds (14, 7, 3 days) are checked once per trading day at the start of the session, not on every 5-minute poll.
- Email notifications use an SMTP-compatible service configured by the trader (e.g., Gmail, SendGrid). Credentials are stored locally and never transmitted externally.
- SMS via Twilio is a stretch goal and not required for initial delivery.
- All persistent data (positions, alerts, tokens, thesis groups, exit goals) is stored on the trader's local machine. No cloud sync or remote backup is in scope.
- The local database is designed so that switching to a hosted Postgres database requires only a configuration change and a schema migration, with no application logic changes.
- Automated trade execution is explicitly out of scope.
- Multi-user support is explicitly out of scope.
- A native mobile app is explicitly out of scope. The web dashboard MUST be responsive and fully functional on mobile viewports.
