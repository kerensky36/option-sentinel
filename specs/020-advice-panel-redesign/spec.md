# Feature Specification: Advice Panel Redesign

**Feature Branch**: `020-advice-panel-redesign`

**Created**: 2026-09-27

**Status**: Draft

**Amends**: `specs/017-macro-quorum-agents/spec.md` FR-001, FR-016, FR-018/`specs/019-demo-quorum-tailored/spec.md` FR-201 (demo result shape), and `specs/018-fundamentals-first-quorum/spec.md` FR-120 (data-use page). Everything else in specs 017–019 is unchanged, including the five seats, the deterministic 3-of-5 tally, the vote request shape and its 60-second limit (018 FR-118), the rate limit, and the rule that results are never stored.

**Input**: User description: "Advice panel redesign for the quorum. Replace the Quorum column with an ADVICE(Agentic) button on each position row, carrying a hazard-stripe warning label. Show results as a radial vote ring, a master summary written by a model from the five votes, and a collapsible row per analyst. Vote colours must not be confused with P&L red/green or the warning yellow. Exit rules are out of scope."

**Reference mock**: `mock/advice-panel-mock.html` (also published at https://claude.ai/artifact/Hsu7gkhdeeSBRfUqEAzsft, revision 3)

## Clarifications

### Session 2026-09-27

- Q: What should the button say? → A: Exactly "ADVICE(Agentic)". The word "Advice" appears only on the button; the panel, error messages and data-use page keep "quorum" wording.
- Q: Where does the button go? → A: On every spread summary row and every standalone option row, next to the position name, so advice can be requested without expanding a spread or opening the payoff graph. The separate Quorum column is removed.
- Q: Which vote colours? → A: HOLD slate grey, ROLL blue, CLOSE orange with a diagonal hatch. This avoids the app's green/red (P&L) and yellow (warnings), is distinguishable under common colour-vision deficiencies, and the colours get "hotter" as more action is suggested. Colour is never the only cue.
- Q: Who writes the master summary? → A: A model (the same Gemini model on Vertex AI as the seats), as one additional call after the votes. The verdict remains computed by the server and is given to the summariser as a fixed input.
- Q: Should the summary say what would change the call? → A: No. That section is dropped because it forecasts price triggers and reads as trade advice.
- Q: Should user exit rules (take-profit / stop-loss) feed into the vote? → A: Not in this feature. Planned as a separate later feature.
- Q: Should the votes appear as soon as they are counted, with the summary following, or should everything appear together? → A: Two steps. The vote request returns the verdict, ring and rows as today; the panel then makes a separate summary request and shows "Writing summary…" until it arrives or fails. The summary never delays the verdict.
- Q: How are numbers in the summary kept honest? → A: The summariser never writes numbers. It receives a catalog of named figures and writes placeholders (e.g. `{captured_pct}`); the server fills in the values. A digit typed by the model or an unknown placeholder removes that "why" bullet or dissent sentence; if it is in the title or explanation, the whole summary is discarded. Seats cite figures the same way, by catalog name.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Request advice from any position row (Priority: P1) 🎯 MVP

A trader looking at the positions dashboard sees an "ADVICE(Agentic)" button, marked with a yellow-and-black hazard stripe, next to the name of every spread and every standalone option. They click it on a collapsed spread. The quorum runs and the result panel opens directly beneath that row. They never had to expand the spread or open the payoff graph.

**Why this priority**: The button is the entry point to the whole feature. Moving it from a far-right column to beside the name makes it visible without horizontal scrolling on narrow screens, and the hazard stripe marks it as AI opinion before it is clicked.

**Independent Test**: Load the dashboard with one spread and one standalone option. Verify both rows show the button beside their names, the table has no Quorum column, and clicking the button on the collapsed spread opens the result panel beneath it without expanding the legs or opening the graph.

**Acceptance Scenarios**:

1. **Given** the positions dashboard with spreads and standalone options, **When** it renders, **Then** every spread summary row and standalone option row shows a button labelled exactly "ADVICE(Agentic)" with a hazard-stripe marker, placed immediately after the position name, and no table column is headed "Quorum".
2. **Given** a collapsed spread, **When** the trader clicks its button, **Then** the spread stays collapsed, the payoff graph does not open, and the result panel (loading state first) appears directly beneath that row.
3. **Given** an open result panel, **When** the trader clicks the same button again, **Then** the panel closes; **When** they click another row's button, **Then** the first panel closes and a new one opens under the other row.
4. **Given** leg rows inside an expanded spread, **When** they render, **Then** they carry no advice button (advice is per position, not per leg).
5. **Given** a phone-width screen (360 px), **When** the dashboard renders, **Then** the button is visible without horizontal scrolling.

---

### User Story 2 - See the vote at a glance (Priority: P1)

When the result arrives, the trader sees a ring with one wedge per analyst. Each wedge is coloured and labelled by its vote and filled out in proportion to that analyst's confidence. The verdict and the count of agreeing analysts sit in the centre, with a tally beneath. Pointing at a wedge highlights that analyst's row, and clicking it expands the row.

**Why this priority**: Replaces the bar tally and five text cards with one picture that answers "what did they say and how sure were they".

**Independent Test**: Render the panel with fixed results for a majority, a no-consensus split, and a no-quorum case with abstentions. Verify the wedges, colours, labels, centre text and tally for each.

**Acceptance Scenarios**:

1. **Given** a result with five valid votes, **When** the ring renders, **Then** it has five equal wedges in fixed seat order. Each wedge is filled from the inner radius in proportion to that seat's confidence (0–100%), its outer band shows the vote's colour, and a text label outside it gives the seat's short name, its vote, its roll direction when rolling, and its confidence.
2. **Given** vote colours, **When** any vote is shown (ring, tally, analyst row, verdict badge), **Then** HOLD is slate grey, ROLL is blue, and CLOSE is orange with a diagonal hatch on filled areas, and the vote name appears as text next to the colour.
3. **Given** a majority verdict, **When** the ring renders, **Then** the centre shows the verdict (for ROLL, "ROLL OUT" or the majority's roll direction) and "N of 5". **Given** NO_CONSENSUS or NO_QUORUM, **Then** the centre shows "NO CONSENSUS" or "NO QUORUM" and the number of seats that voted.
4. **Given** an abstaining seat, **When** the ring renders, **Then** its wedge is empty (neutral) and labelled "ABSTAIN".
5. **Given** the pointer over a wedge (or keyboard focus on it), **Then** that seat's row is highlighted; **When** the wedge is clicked or activated with Enter/Space, **Then** that row expands and scrolls into view.
6. **Given** any result, **Then** a tally beneath the ring lists CLOSE, HOLD and ROLL counts (plus ABSTAIN when non-zero), with the winning action emphasised.

---

### User Story 3 - Read one summary of the quorum's reasoning (Priority: P2)

Beside the ring, the trader reads a short summary that pulls the five rationales together: a one-line call, a short explanation, bullets for why the majority voted as it did, and a paragraph on the dissent. It never contradicts the verdict and only quotes figures that the analysts or the position data actually contain.

**Why this priority**: Five separate rationales take time to read and weigh. The summary gives the gist in one place. It depends on the votes, so it ranks after the ring.

**Independent Test**: With the model stubbed, verify: a valid summary renders in its four parts; a summary whose title names a different action is discarded; placeholders are filled with the server's values; a raw digit or unknown placeholder in a bullet removes only that bullet, and in the title removes the whole summary; a summariser timeout shows "Summary unavailable" while the ring and rows still render; a no-quorum result shows fixed text and makes no summary request; a vote result altered before being sent for summary is rejected.

**Acceptance Scenarios**:

1. **Given** a result with a verdict of CLOSE, HOLD, ROLL or NO_CONSENSUS, **When** the vote result renders, **Then** the summary area shows "Writing summary…" and the panel makes one separate summary request, whose single model call produces a summary with: a title (one line), an explanation (at most 3 sentences), "why" bullets (1–4), and a dissent paragraph. The panel headings read "Why the majority" for a verdict and "Where the votes fell" for NO_CONSENSUS.
2. **Given** the summariser returns a title that names an action other than the verdict (for NO_CONSENSUS: names CLOSE or ROLL as the thing to do), **When** the server checks it, **Then** the summary is discarded and the panel shows "Summary unavailable".
3. **Given** the summariser output, **When** the server checks it, **Then** every placeholder naming a catalog figure is replaced by that figure's value as displayed elsewhere in the panel; a "why" bullet or dissent sentence containing a digit the model typed itself, or an unknown placeholder, is removed; and if the title or explanation contains either, the whole summary is discarded and the panel shows "Summary unavailable".
4. **Given** the summary request fails, returns malformed output, or exceeds its time budget, **Then** the verdict, ring, tally and analyst rows stay as rendered, and the summary area changes from "Writing summary…" to "Summary unavailable".
5. **Given** a NO_QUORUM result, **Then** no summary request is made and the summary area shows fixed text stating how many analysts voted and that there is no recommendation.
6. **Given** all voting analysts agree, **Then** the dissent paragraph states that there was no dissent.
7. **Given** demo mode, **Then** the summary is built in the browser from fixed templates over the demo votes, with no network request.

---

### User Story 4 - Drill into each analyst (Priority: P2)

Below the ring and summary, each analyst has one collapsed row showing their lens, vote (with roll direction), and a confidence bar with percentage. Expanding a row shows the full rationale and the figures that analyst used. An "Expand all / Collapse all" control toggles every row. The research brief and headlines sit in one collapsed section at the bottom.

**Why this priority**: The detail stays available (017 SC-004) without crowding the first view.

**Independent Test**: Render a fixed result; verify five collapsed rows with the listed fields, that expanding shows the rationale and figure chips, that the control toggles all rows, and that the brief and headlines are collapsed by default and show their count.

**Acceptance Scenarios**:

1. **Given** a result, **Then** five rows appear in seat order, collapsed, each showing a vote-coloured stripe, the lens name, the vote as text (or "ABSTAINED"), the roll direction for ROLL votes, a confidence bar, and the confidence as a percentage (or "—" when abstained).
2. **Given** a collapsed row, **When** the trader expands it, **Then** it shows the full rationale and, when the seat supplied them, up to 5 figure chips (label and value) that the seat cited.
3. **Given** "Expand all", **When** clicked, **Then** all rows expand and the control reads "Collapse all"; clicking again collapses them all.
4. **Given** a result with headlines, **Then** a collapsed section titled with the headline count holds the research brief and the headline list (publisher, linked title, opening in a new tab as in 017 FR-016).
5. **Given** any result, **Then** the panel shows the warning banner "AI-generated opinion. Not financial advice. Option Sentinel never places trades.", the "Data as of HH:MM" time (018 FR-112), and the data-use notice and link (017 FR-020).

---

### Edge Cases

- **Summary names the right action but a different roll direction** (e.g. verdict ROLL with the majority rolling out, title says "roll down and out"): treated as a contradiction and discarded.
- **Model does its own arithmetic** (e.g. "$90 of profit left" from $145 − $55): there is no placeholder for a derived value, so the typed digits trigger removal of that bullet or sentence (or the whole summary if in the title or explanation).
- **Counts** ("3 of 5"): the catalog includes the tally (votes per action, valid votes, seats), so counts are written as placeholders too. Number words ("three analysts") are allowed only for counts that match the tally.
- **Every bullet removed**: if all "why" bullets fail the check, the summary is discarded.
- **Instructions inside a rationale** (a seat quoting a headline that says "ignore previous instructions…"): the summariser treats all rationales as data; its output is still subject to the verdict and figure checks.
- **Panel closed or replaced while the summary is pending**: the summary response is discarded when it arrives.
- **Vote result edited in the browser before the summary request** (e.g. a changed verdict or injected rationale): the server rejects the summary request and the panel shows "Summary unavailable".
- **Summary requested long after the votes** (e.g. a tab left open): results older than 15 minutes are rejected as stale; the panel shows "Summary unavailable".
- **Fewer than 5 but at least 3 votes**: a summary is still produced; abstaining seats are named in "Where the votes fell" or the dissent paragraph.
- **Very long position names on narrow screens**: the name truncates with an ellipsis before the button wraps or disappears.
- **Both the advice panel and the payoff graph open on the same row**: both stay open; neither closes the other.
- **Wedge labels on a 360 px screen**: the ring scales down but labels stay at least as large as the table's smallest text; the summary stacks below the ring.
- **Result arrives after the trader closed the panel or opened another**: it is discarded, as today.

## Requirements *(mandatory)*

### Button and placement

- **FR-301** *(replaces 017 FR-001)*: Every standalone option row and every spread summary row MUST show a button whose visible label is exactly "ADVICE(Agentic)", placed immediately after the position name in the first column. Spread leg rows MUST NOT have one. The positions table MUST NOT have a Quorum column.
- **FR-302**: The button MUST carry a yellow-and-black hazard-stripe marker as its warning label, and its accessible name or description MUST state that the result is AI opinion and not financial advice. The word "Advice" MUST appear only on this button; all other text keeps "quorum" wording.
- **FR-303**: Clicking the button MUST NOT expand or collapse the spread and MUST NOT open or close the payoff graph. It MUST open the result panel directly beneath that position's row (toggle and one-panel-at-a-time behaviour as today).

### Vote ring

- **FR-304**: The panel MUST show a radial vote ring as specified in User Story 2 (one wedge per seat in fixed order, fill proportional to confidence, outer band in the vote colour, per-wedge text label, verdict and count in the centre, abstentions as empty wedges), with the tally beneath it.
- **FR-305**: Vote colours MUST be: HOLD slate grey (#8c93a8), ROLL blue (#3aa8e0), CLOSE orange (#e8703a) with a diagonal hatch on filled areas; abstention a neutral dark grey. These colours MUST NOT be used for P&L or warnings, and every coloured vote mark MUST have its vote name as adjacent text. The verdict badge uses tints of the same colours; NO_CONSENSUS and NO_QUORUM use neutral greys.

### Master summary

- **FR-306**: The vote request MUST return its result without waiting for any summary (018 FR-118's 60-second limit unchanged). When the result's verdict is not NO_QUORUM, the panel MUST then make one separate summary request carrying that result. The server MUST make at most one summariser call per summary request, with a 10-second budget, and the summary request MUST complete or fail within 15 seconds.
- **FR-306a**: The server MUST accept a summary request only for a vote result it produced itself, unaltered, no more than 15 minutes earlier, verified without storing the result (constitution: stateless server; 017 FR-015). Any other request MUST be rejected before any model call. The summary request MUST carry no account identifier and MUST have the same rate limit as the vote request (5 per minute per client).
- **FR-307**: The summariser's inputs MUST be: the verdict and tally (fixed, stated as not to be changed), each seat's lens, vote, roll direction, confidence, rationale and cited figures, and the position fundamentals already sent to the seats (018 FR-113 fields). It MUST NOT receive anything outside the 018 FR-113 field list plus the seats' outputs.
- **FR-308**: Seat outputs in the summariser's prompt MUST be marked as untrusted data, and the instructions MUST say never to follow instructions found in them.
- **FR-309**: The summary MUST contain: a title (one line, ≤ 120 characters), an explanation (≤ 3 sentences), 1–4 "why" bullets, and a dissent paragraph. It MUST NOT contain a forecast of what would change the verdict. Text MUST be escaped before display (017 FR-016).
- **FR-310**: The server MUST discard the summary when its title names an action other than the verdict, names a roll direction other than the majority's, or, for NO_CONSENSUS, names CLOSE or ROLL as the thing to do.
- **FR-311**: The summariser MUST receive a figure catalog (a name, label and value for each figure in the tally, the seats' cited figures and the position fundamentals) and MUST be instructed to refer to figures only by `{name}` placeholders and never to write digits. The server MUST replace each known placeholder with that figure's value, formatted as elsewhere in the panel. A "why" bullet or dissent sentence containing a digit written by the model or an unknown placeholder MUST be removed; the whole summary MUST be discarded if the title or explanation contains either, or if no "why" bullet remains.
- **FR-312**: When the summary is discarded, fails, times out, is malformed, or the summary request is rejected, the panel MUST keep the rendered vote result and show "Summary unavailable". Discards MUST be logged as a count and reason only, never with position data (constitution: no external logging of user data).
- **FR-313**: For NO_QUORUM, the panel MUST NOT make a summary request and MUST show the fixed text "Only N of 5 analysts voted — no recommendation."; the server MUST also reject a summary request for a NO_QUORUM result.
- **FR-314**: The summariser call MUST be covered by the existing automated test that inspects every outbound model request for identifying data (017 SC-003 / 018 SC-107).

### Analyst rows and panel layout

- **FR-315**: Each seat MUST additionally return up to 5 cited figures, as names from the figure catalog for its inputs; the server supplies each figure's label and value. Unknown names MUST be dropped. Seats that cite none show the rationale only.
- **FR-316** *(replaces 017 FR-016's layout)*: The panel MUST show, in order: verdict badge with the position and "N of 5" note and "Data as of" time; the warning banner (FR-317); the ring and tally beside the summary area, which reads "Writing summary…" while the summary request is pending (stacked on narrow screens); the five collapsible analyst rows with an Expand all / Collapse all control; a collapsed "Research brief & headlines (N)" section; the disclaimer and data-use notice (017 FR-017, FR-020).
- **FR-317**: The warning banner MUST read "AI-generated opinion. Not financial advice. Option Sentinel never places trades." and MUST be visible without expanding anything.
- **FR-318**: Row expansion state MUST NOT be persisted (017 FR-015 unchanged); closing the panel discards it.
- **FR-319**: The panel MUST be usable at 360 px width without horizontal page scrolling: the panel stays within the visible width even when the table scrolls sideways; ring labels, row fields and the summary remain legible.
- **FR-320**: Wedges and rows MUST be operable by keyboard (focusable, Enter/Space to expand) and have visible focus.

### Demo mode and disclosure

- **FR-321** *(amends 019 FR-201)*: In demo mode the result MUST also include a summary and cited figures built in the browser from fixed templates over the demo votes and figures, with no network request, and labelled as demo.
- **FR-322** *(amends 018 FR-120)*: The "How we use your data" page MUST state that one additional Vertex AI request per quorum sends the analysts' votes and rationales together with the same position fields, to produce the summary, and that nothing is retained.

### Key Entities

- **Figure Catalog**: The named figures the server makes available to seats and summariser (name, label, display value), built from the position fundamentals and the tally. Values always come from the server, never from a model.
- **Cited Figure**: A catalog figure a seat chose to cite (e.g. "IV/RV" → "1.08×"). Belongs to one analyst vote; at most 5 per vote.
- **Quorum Summary**: Title, explanation, "why" bullets, dissent paragraph. Returned by the summary request for one quorum result; shown in the panel as pending, available, unavailable, or fixed (NO_QUORUM text). Never stored.
- **Quorum Result** *(extended)*: Gains, per vote, the cited figures, and a server-issued integrity seal that lets the server later confirm it produced the result unaltered and when. All other fields as in spec 018.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-301**: A trader can request advice on any position from the dashboard in one click, with no need to expand a spread, open the graph, or scroll sideways, at widths from 360 px up.
- **SC-302**: In automated tests over all verdict types, a summary whose title contradicts the verdict or roll direction is never displayed (100% discarded).
- **SC-303**: In automated tests, no number written by a model is ever displayed in the summary or the cited figures: every displayed number comes from the figure catalog (100%).
- **SC-304**: When the summariser fails or times out, 100% of results still show the verdict, ring, tally and all analyst rows.
- **SC-305**: No NO_QUORUM result triggers a summariser call (verified by automated test).
- **SC-306**: The time to show the verdict, ring and analyst rows is no longer than in the spec 018 build for the same position (the summary adds nothing to it). The summary appears or is marked unavailable within 15 seconds of the verdict in every case.
- **SC-310**: 100% of summary requests carrying an altered, foreign, NO_QUORUM, or older-than-15-minute result are rejected before any model call (verified by automated test).
- **SC-307**: A trader can tell every vote apart without relying on colour (text label on every vote mark; hatch on CLOSE), verified by checking the panel in greyscale.
- **SC-308**: No identifying data appears in any model request, including the summariser call (017 SC-003 re-verified).
- **SC-309**: In a review of at least 10 live results, every summary's title matches the verdict, and at least 8 of 10 summaries are shown in full (no bullet removed and not discarded).

## Assumptions

- The summariser uses the same model and Vertex AI configuration as the seats; no new provider or credential.
- A 10-second summariser budget is enough for a short structured output.
- The vote request's rate limit (5 per minute) is unchanged; the summary request gets its own limit of the same size, so one click (one vote plus one summary request) never trips either limit on its own.
- Cited figures come from the seats themselves rather than being inferred afterwards, so each seat's output format gains one optional list.
- Seat rationales keep quoting figures in their own words, as in spec 018 (FR-115); the placeholder rule applies to the summary and to the cited-figure chips only.
- The hazard-stripe yellow on the button and warning banner stays as today; the vote palette deliberately avoids it.
- User-defined exit rules (take-profit, stop-loss, days-to-expiry review) are out of scope and planned as a separate feature.
