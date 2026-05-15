# Feature Specification: Fix Covered Call Screener — 100-Share Lot Filter

**Feature Branch**: `007-fix-lot-size-filter`
**Created**: 2026-05-14
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Valid Lot Filter (Priority: P1)

As a trader reviewing covered call opportunities, I only want to see positions where I hold enough shares to write at least one standard contract. A position with 50 or 150 shares cannot be used to write a covered call because options are sold in 100-share lots. The screener should silently omit those positions rather than show them with misleading or incorrect contract counts.

**Why this priority**: This is a correctness bug — showing opportunities on ineligible positions is misleading and could result in a trader attempting a trade that their broker will reject.

**Independent Test**: Open the screener with a portfolio containing positions of varying share counts (e.g., 50, 100, 150, 200, 300). Confirm only positions with shares divisible by 100 appear in results.

**Acceptance Scenarios**:

1. **Given** a position with exactly 100 shares, **When** the screener runs, **Then** the position appears with 1 available contract.
2. **Given** a position with 200 shares, **When** the screener runs, **Then** the position appears with 2 available contracts.
3. **Given** a position with 50 shares, **When** the screener runs, **Then** the position is not shown in screener results.
4. **Given** a position with 150 shares, **When** the screener runs, **Then** the position is not shown in screener results.
5. **Given** a position with 300 shares, **When** the screener runs, **Then** the position appears with 3 available contracts.
6. **Given** all positions have non-lot-sized share counts, **When** the screener runs, **Then** the results list is empty with a clear "no eligible positions" message.

---

### Edge Cases

- Position with exactly 0 shares: must not appear.
- Short positions (negative share count): must not appear.
- Portfolio with a mix of eligible and ineligible positions: only eligible positions are shown; ineligible ones are silently filtered with no error.
- The available contracts count must always equal floor(shares) ÷ 100 with no rounding up.
- Fractional share quantities (e.g., 100.5): floor to integer first, then apply divisibility check. A position with 100.5 shares yields 1 contract; a position with 150.9 shares is ineligible.
- Multi-account portfolios: lot-size eligibility is evaluated per account independently. Shares are never aggregated across accounts — a position must meet the 100-share threshold within its own account to be eligible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The screener MUST exclude any position where floor(shares held) is not a positive multiple of 100. For fractional share quantities, the integer part is used; the raw fractional quantity is never compared directly against the threshold.
- **FR-002**: For eligible positions, the screener MUST display the number of available contracts as shares ÷ 100 (integer division, no rounding up).
- **FR-003**: When no positions meet the lot-size requirement, the screener MUST display a clear message indicating there are no eligible positions rather than an empty or broken view.
- **FR-004**: The lot-size filter MUST be applied before any covered call calculations to avoid presenting misleading premium or return figures on ineligible positions.
- **FR-005**: The screener MUST NOT display any intermediate or partial results while loading. All results are held until the full lot-size check is complete; only eligible positions are then rendered atomically.
- **FR-006**: After the initial load, portfolio position data MUST be cached in memory for the duration of the session. Subsequent screener loads MUST use the cached data (no re-fetch from Schwab) unless the user explicitly triggers a refresh or erases all data.
- **FR-007**: The in-memory portfolio cache MUST be cleared on logout. It MUST also be invalidated when the user clicks the refresh control or erases all data.

### Key Entities

- **Position**: A holding in a single equity. Relevant attributes: symbol, shares held (must be a positive multiple of 100 to be eligible).
- **Screener Result**: A covered call opportunity derived from an eligible position. Relevant attributes: symbol, available contracts (= shares ÷ 100), premium metrics.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of positions shown in screener results have share counts that are positive multiples of 100.
- **SC-002**: The available contracts count shown for every result equals shares ÷ 100 exactly — no rounding up or approximation.
- **SC-003**: Zero screener results appear for positions with share counts not divisible by 100, verified across all test portfolio configurations.
- **SC-004**: When all positions are ineligible, the screener displays a non-empty "no eligible positions" message within the same response time as a normal result.
- **SC-005**: After initial load, subsequent screener renders (using cached portfolio data) complete in under 1 second with no Schwab API call.
- **SC-006**: The portfolio cache is absent (cleared) immediately after logout. Verifiable by inspecting in-memory state or confirming a fresh Schwab fetch occurs on next login.

## Assumptions

- Standard options contracts are always 100 shares. Mini-options (10-share lots) are out of scope.
- "Shares held" refers to the long share quantity in the position. Short positions are ineligible. Fractional share quantities are not rejected — the integer part (floor) is used: if floor(shares) is a positive multiple of 100, the position is eligible and available contracts = floor(shares) ÷ 100.
- The fix applies to the screener logic only; no changes to UI layout are required beyond reflecting the corrected contract counts and the empty-state message.
- Positions with lot-sized share counts that have other issues (e.g., no options chain available) may still be excluded by existing screener logic — this fix only adds the lot-size gate.
- Schwab's API does not provide server-side lot-size filtering; the 100-share divisibility check is implemented entirely in the application's screener service layer.

## Clarifications

### Session 2026-05-15

- Q: Where should the lot-size filter be enforced (backend, frontend, or both)? → A: Backend/screener service layer only, scoped strictly to the covered call screener. This rule does not apply globally across all pages or features — only where the 100-share lot requirement is relevant (i.e., covered call eligibility checks).
- Q: For multi-account portfolios, should lot-size eligibility be evaluated per account or by aggregating shares across accounts? → A: Per account — each account's position is evaluated independently; shares are never combined across accounts.
- Q: How should fractional share quantities (e.g., 100.5) be handled — reject or truncate? → A: Eligible if floor(shares) is a positive multiple of 100; integer part is used for contract count. E.g., 100.5 → 1 contract, 150.9 → ineligible.
- Q: Should ineligible positions be visible temporarily during loading, or held until the full filter runs? → A: Hold all results until lot-size check is complete; only eligible positions are rendered atomically — no intermediate state shown.
- Q: What is the latency target for screener loads? → A: Initial load has no strict ceiling (Schwab API round-trip). After initial load, portfolio is cached in memory; subsequent renders must be sub-second. Cache is invalidated on: user-triggered refresh, erase all data, or logout.
