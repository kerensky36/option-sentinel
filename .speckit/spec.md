# Feature Specification: Option Sentinel

**Feature Branch**: `001-option-sentinel-monitor`  
**Created**: 2026-04-28  
**Status**: Draft  
**Input**: User description: "Personal options position monitor that connects to the Schwab API, automatically tracks open positions, fires alerts when pre-defined trading rules trigger, and displays a live dashboard."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Live Position Dashboard (Priority: P1)

A trader opens the Option Sentinel dashboard and immediately sees all of their current open options positions. Each position displays its current market value, unrealised P&L, days to expiry, and thesis alignment status. The data reflects the latest available market prices, refreshed automatically during trading hours.

**Why this priority**: Without a clear view of open positions, none of the alerting or management features have context. This is the foundational view the trader relies on throughout the trading day.

**Independent Test**: Can be tested by connecting to a brokerage account with at least one open position, opening the dashboard, and verifying that the position appears with accurate data fields. Delivers standalone value as a position viewer even before any alert rules are active.

**Acceptance Scenarios**:

1. **Given** the trader has open options positions in their brokerage account, **When** they open the dashboard, **Then** all open positions are displayed with symbol, option type, strike, expiry date, quantity, current mark price, unrealised P&L, days to expiry, and thesis alignment tag.
2. **Given** the dashboard is open during market hours, **When** the data refresh interval elapses, **Then** position values update to reflect current market prices without a manual page reload.
3. **Given** the market is closed, **When** the trader opens the dashboard, **Then** positions are still visible with the last known values and a clear indication that live prices are unavailable.

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

### User Story 5 - Thesis Alignment Tagging (Priority: P3)

The trader assigns each open position a thesis alignment status — aligned or misaligned with their current market thesis. This tag is visible on the dashboard, allowing the trader to quickly identify positions they may want to re-evaluate as the market environment changes.

**Why this priority**: Thesis alignment is a qualitative risk management tool. It adds context to each position but does not drive automated alerts, making it lower priority than the core alerting rules.

**Independent Test**: Can be tested by opening a position, assigning "aligned" and "misaligned" tags, and confirming the correct label persists on the dashboard after a page refresh.

**Acceptance Scenarios**:

1. **Given** an open position is displayed on the dashboard, **When** the trader sets its thesis alignment to "aligned" or "misaligned", **Then** the updated tag is immediately visible on the position row.
2. **Given** a position has a thesis alignment tag, **When** the trader changes it, **Then** the new tag is persisted and survives a page refresh.
3. **Given** a position has no tag set, **When** it is displayed on the dashboard, **Then** it shows a neutral untagged state rather than defaulting to either alignment.

---

### Edge Cases

- What happens when the brokerage account has no open positions? Dashboard shows an empty state with a clear message rather than an error.
- What happens when the access token expires mid-poll? System silently refreshes the token and retries the poll; the user sees no interruption.
- What happens when the refresh token expires (7-day window)? The system surfaces a prominent re-authentication prompt and pauses polling until the user re-authenticates.
- What happens when a position simultaneously triggers both a profit-target alert and a 3-day expiry alert? Both alerts are delivered independently.
- What happens when a position is partially closed at the brokerage? Position data reflects the current remaining quantity; alerts recalculate against the updated figures.
- What happens when the market is closed and the binary event flag is raised? The full-exit alert fires immediately regardless of market hours; polling suspension does not block this alert.
- What happens if email delivery fails? The alert is logged locally and retried on the next poll cycle up to 3 attempts before being marked failed.

## Requirements *(mandatory)*

### Functional Requirements

**Position Tracking**

- **FR-001**: The system MUST connect to the trader's brokerage account and retrieve all open options positions automatically.
- **FR-002**: The system MUST refresh position data every 5 minutes while the market is open (US equity market hours: 9:30 AM – 4:00 PM ET, Monday–Friday, excluding US market holidays).
- **FR-003**: All position data MUST be stored locally and MUST NOT be transmitted to any external service other than the brokerage API.
- **FR-004**: The system MUST handle brokerage access token expiry transparently, refreshing tokens automatically without user intervention.
- **FR-005**: The system MUST detect when the brokerage refresh token is nearing its 7-day expiry and display a clear re-authentication prompt to the trader before polling is interrupted.

**Dashboard**

- **FR-006**: The dashboard MUST display all open positions with: underlying symbol, option type, strike, expiry date, quantity, current mark price, unrealised P&L, days to expiry, and thesis alignment status.
- **FR-007**: The dashboard MUST show when the last successful data refresh occurred and the current polling status.
- **FR-008**: The dashboard MUST display a visible banner or indicator when the binary event flag is active.
- **FR-009**: The dashboard MUST allow the trader to raise and clear the binary event flag.
- **FR-010**: The dashboard MUST allow the trader to set and change the thesis alignment tag (aligned / misaligned / untagged) for any open position.

**Alerting — Close Trigger**

- **FR-011**: The system MUST calculate the maximum profit for each credit spread based on the net credit received at open.
- **FR-012**: The system MUST fire an email alert when a credit spread position's mark indicates that 50% or more of its maximum profit has been captured.
- **FR-013**: The close-trigger alert MUST NOT repeat for the same position within the same trigger event; it re-arms only after the position drops below the threshold and re-crosses it.

**Alerting — Expiry Warnings**

- **FR-014**: The system MUST send an email alert when an open position reaches 14 calendar days to expiry.
- **FR-015**: The system MUST send an email alert when an open position reaches 7 calendar days to expiry.
- **FR-016**: The system MUST send an email alert when an open position reaches 3 calendar days to expiry.
- **FR-017**: Each expiry warning tier MUST fire only once per position per threshold crossing.

**Alerting — Binary Event Exit**

- **FR-018**: When the trader raises the binary event flag, the system MUST immediately send a single consolidated email listing all open positions with an instruction to exit all positions.
- **FR-019**: The binary event alert MUST fire once per flag-raise event; re-raising the flag after it has been cleared triggers a new alert.

**Alerting — Delivery**

- **FR-020**: The system MUST deliver alerts via email as the primary notification channel.
- **FR-021**: The system MUST log all alert events locally with timestamp, alert type, position reference, and delivery status.
- **FR-022**: Failed alert deliveries MUST be retried up to 3 times before being marked as permanently failed in the local log.

### Key Entities

- **Position**: A single open options leg or spread. Key attributes: underlying symbol, option type, strike, expiry date, quantity, opening credit/debit, current mark value, thesis alignment tag, open/closed status.
- **Spread**: Groups related position legs into a named strategy (e.g., credit spread). Key attributes: strategy type, maximum profit, maximum loss, net credit received, member legs.
- **Alert**: A triggered notification event. Key attributes: alert type, position or spread reference, severity, trigger timestamp, delivery status, retry count, acknowledged timestamp.
- **AuthToken**: Brokerage OAuth token state. Key attributes: access token, access expiry, refresh token, refresh expiry, re-auth required flag.
- **BinaryEventFlag**: The trader's manual full-exit signal. Key attributes: active state, activated timestamp, cleared timestamp.
- **ThesisTag**: The alignment label on a position. Values: `aligned`, `misaligned`, `untagged`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All open positions are visible on the dashboard within 10 minutes of being opened at the brokerage (at most two poll cycles).
- **SC-002**: Alert notifications are delivered within 5 minutes of the triggering condition being detected during a poll.
- **SC-003**: The binary event exit alert is delivered within 60 seconds of the trader raising the flag.
- **SC-004**: The trader can tag or re-tag any position's thesis alignment in under 30 seconds from the dashboard.
- **SC-005**: The system operates continuously during market hours with zero unplanned polling interruptions caused by token expiry.
- **SC-006**: No position data is transmitted to any destination other than the brokerage API (verifiable by network inspection).
- **SC-007**: 100% of triggered alerts for the 3-day expiry threshold and the close-trigger rule result in a delivered or logged-retry notification.
- **SC-008**: The re-authentication prompt appears at least 24 hours before the refresh token expires.

## Assumptions

- The trader operates a single brokerage account; multi-account support is out of scope.
- "Market hours" means US equity market hours: 9:30 AM – 4:00 PM ET, Monday through Friday, excluding US market holidays. The holiday calendar is embedded in the application and updated annually.
- The trader's brokerage (Charles Schwab) provides a publicly accessible OAuth2 API supporting position retrieval. No internal or institutional API access is assumed.
- The net credit received for each spread is either returned by the brokerage API as cost-basis data or entered manually by the trader at position open, as the API may not expose this value in a directly usable format.
- Expiry warning thresholds (14, 7, 3 days) are checked once per trading day at the start of the session, not on every 5-minute poll.
- Email notifications use an SMTP-compatible service configured by the trader (e.g., Gmail, SendGrid). Credentials are stored locally and never transmitted externally.
- SMS via Twilio is a stretch goal and not required for initial delivery.
- All persistent data (positions, alerts, tokens) is stored on the trader's local machine. No cloud sync or remote backup is in scope.
- The local database is designed so that switching to a hosted Postgres database requires only a configuration change and a schema migration, with no application logic changes.
- Automated trade execution is explicitly out of scope.
- Multi-user support is explicitly out of scope.
- Mobile app support is explicitly out of scope.
