# Feature Specification: Screener Risk Tolerance Controls

**Feature Branch**: `013-screener-risk-tolerance`  
**Created**: 2026-05-17  
**Status**: Draft  
**Input**: User description: "Add risk tolerance controls to the covered call screener."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Switch Risk Profile, Results Re-Rank Instantly (Priority: P1)

A trader opens the covered call screener and sees results ranked under the default Balanced profile. They switch to Conservative — wanting less assignment risk — and the results immediately re-order to surface lower-delta, further-OTM candidates at the top. No loading spinner, no waiting for the broker. Switching back to Balanced or forward to Aggressive is equally instant.

**Why this priority**: This is the core value of the feature. If re-ranking requires a round-trip to the broker the UX is no better than refreshing the page.

**Independent Test**: Load the screener, note the ranking order, switch profile, confirm ranking changes within one animation frame with no network request issued.

**Acceptance Scenarios**:

1. **Given** the screener has loaded results, **When** the trader selects Conservative, **Then** results re-rank with the most OTM, lower-yield-but-safer candidates at the top and no broker API call is made.
2. **Given** Conservative is active, **When** the trader selects Aggressive, **Then** results re-rank to surface higher-delta, higher-yield candidates at the top instantly.
3. **Given** any profile is active, **When** the trader refreshes broker data, **Then** the active profile is applied to the fresh results automatically.

---

### User Story 2 - Initial Load Covers Full Candidate Range (Priority: P1)

A trader loads the screener for the first time in a session. Behind the scenes the system fetches all liquid option candidates across a wide expiry window (7–60 days) for each stock position, not just the 30–45 day slice used today. The trader sees the same page load time as before, but all future profile switches draw from this richer dataset without any additional data fetch.

**Why this priority**: This is what makes US1 possible. Without a wider fetch, switching to Aggressive (which may prefer shorter DTE) would have no candidates to show.

**Independent Test**: Load the screener and confirm that switching to Aggressive surfaces options with DTE below 30 when they exist — proving the wider window was fetched.

**Acceptance Scenarios**:

1. **Given** a stock position with liquid options at 14 DTE, **When** the screener loads with Aggressive profile, **Then** those short-DTE options appear as candidates.
2. **Given** the screener has loaded, **When** the trader switches between all three profiles, **Then** no additional broker requests are made.
3. **Given** no liquid options exist in the 7–60 day window for a ticker, **Then** that ticker is shown as insufficient data regardless of profile.

---

### User Story 3 - Fine-Grained Sliders for Custom Profile (Priority: P2)

A trader wants to go beyond the three presets and dial in their exact preferences: a specific target delta (e.g. 0.20), a custom DTE range (e.g. 21–35 days), and their own weighting between yield and safety. They expand an advanced panel to reveal individual sliders and adjust them. Results re-rank after each slider change, still with no additional broker calls.

**Why this priority**: The three presets cover most traders. Fine-grained control is a power-user enhancement that depends on US1 and US2 being solid first.

**Independent Test**: Set target delta to 0.20 via slider, confirm the recommended strikes shift OTM compared to the 0.25 default with no network request.

**Acceptance Scenarios**:

1. **Given** the advanced panel is open, **When** the trader moves the target delta slider to 0.20, **Then** rankings update instantly to favour options closer to 0.20 delta.
2. **Given** a custom DTE range of 21–35 days is set, **When** results update, **Then** only options within that DTE range are considered as candidates.
3. **Given** yield weight is increased to 50%, **Then** higher-yield options rank higher even if their delta is less ideal.

---

### User Story 4 - Profile Selection Persists Within the Session (Priority: P2)

A trader selects Aggressive, navigates away to the positions tab, then returns to the screener. Their Aggressive profile is still active — they do not have to re-select it.

**Why this priority**: Losing the selection on navigation is a minor but noticeable friction point. Session persistence is a low-effort quality-of-life improvement.

**Independent Test**: Select Aggressive, navigate to positions tab, return to screener, confirm Aggressive is still active.

**Acceptance Scenarios**:

1. **Given** Aggressive is selected, **When** the trader navigates away and returns, **Then** Aggressive is still the active profile and results reflect it.
2. **Given** the trader closes the tab, **When** they open a new tab and log in, **Then** the profile resets to Balanced (session data does not persist across tabs or sessions).

---

### Edge Cases

- What if a ticker has no liquid candidates in the wider 7–60 day window? Show as insufficient data — same behaviour as today.
- What if the trader is on mobile? The profile toggle must be usable on small viewports; the fine-grained sliders panel should collapse by default on mobile.
- What if all candidates for a ticker fall outside the user's custom DTE range? Treat as no liquid options — show insufficient data rather than falling back to outside the range.
- What if the user's custom slider values produce no ranked results? Show an empty recommended list with a message indicating the parameters filtered out all candidates; suppressed rows still show.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The screener data fetch MUST cover the full 7–60 day expiry window on every load, returning all liquid candidates per ticker.
- **FR-002**: The screener result view MUST include three preset profiles: Conservative, Balanced, and Aggressive.
- **FR-003**: Selecting a profile MUST re-rank and re-render results without issuing any broker API request.
- **FR-004**: The active profile MUST persist for the duration of the browser session and reset to Balanced when the session ends.
- **FR-005**: Conservative profile MUST favour lower-delta (further OTM), lower-risk candidates; Aggressive MUST favour higher-delta, higher-yield, shorter-DTE candidates; Balanced MUST match current default behaviour.
- **FR-006**: A fine-grained advanced panel MUST allow independent adjustment of: target delta (range 0.10–0.45), DTE window (range 7–60 days), and score weight distribution between yield and safety.
- **FR-007**: Fine-grained slider changes MUST re-rank results without any broker API call.
- **FR-008**: The positions tab and positions data fetch MUST be completely unaffected by this feature.
- **FR-009**: Suppressed and insufficient-data rows MUST continue to appear below recommended rows regardless of the active profile.
- **FR-010**: The toggle and advanced panel MUST be usable on mobile viewports.

### Key Entities

- **RiskProfile**: Named preset (Conservative, Balanced, Aggressive) or Custom; encapsulates target delta, DTE range, and score weights.
- **CandidateSet**: All liquid options returned per ticker across the 7–60 day window — the raw material for client-side re-scoring.
- **ScoredResult**: A ticker ranked under a specific RiskProfile — derived client-side from CandidateSet.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Profile switching re-ranks all results in under 100 milliseconds with no network request.
- **SC-002**: For a portfolio with 3+ stock positions, each of the three presets produces a different top-ranked ticker at least once across a typical market day.
- **SC-003**: Screener initial load time increases by no more than 20% compared to the current narrow-window fetch (wider window, same number of API calls).
- **SC-004**: The profile toggle and results table are fully usable on a 375px-wide mobile viewport without horizontal scrolling.
- **SC-005**: The active profile survives navigation to another tab and back within the same browser session.

## Assumptions

- The wider 7–60 day DTE window will return more option contracts per ticker but the same number of Schwab API calls (one per ticker, already parallelised as of feature 012).
- "Liquid" is defined the same way as today: bid ≥ $0.05 and open interest ≥ 100 contracts.
- Fine-grained sliders are in scope for this feature at P2 priority; if time-boxed they can be deferred without breaking the P1 toggle.
- The Balanced preset exactly reproduces today's screener ranking for any given market snapshot — it is the no-regression baseline.
- Earnings suppression logic (days_to_earnings) is applied before profile scoring and is unaffected by profile selection.
- Score weight distribution in fine-grained mode is a single "Safety ↔ Yield" axis; IV rank weight remains fixed at 50% and the remaining 50% is split between yield and delta safety.
