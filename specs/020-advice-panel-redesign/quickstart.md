# Quickstart: Advice Panel Redesign

GCP and Vertex AI setup is unchanged; see `specs/017-macro-quorum-agents/quickstart.md`. One addition: set a shared seal key for the summary token.

```bash
export QUORUM_SEAL_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

Without it, votes work and the panel shows "Summary unavailable" (D-303).

## Automated checks

```bash
pytest tests/unit/test_figure_catalog.py tests/unit/test_quorum_summary.py \
       tests/unit/test_quorum_ui.py tests/unit/test_quorum_agents.py \
       tests/unit/test_demo_quorum.py tests/unit/test_deploy_backend.py \
       tests/contract/test_quorum_api.py tests/contract/test_data_use_page.py -q
pytest -q   # full suite must stay green
```

The Node-based tests (`test_quorum_ui.py`, `test_demo_quorum.py`) need `node` on PATH and are skipped without it.

| Check | Proves |
|---|---|
| Rendered positions table: no "Quorum" `<th>`; each spread summary and standalone row has exactly one `ADVICE(Agentic)` button in its first cell; leg rows have none | FR-301 |
| Button HTML has the hazard marker and an accessible description with "not financial advice"; no other panel string contains "Advice" | FR-302 |
| Button click handler stops propagation; spread toggle and graph handlers not called (harness with stub DOM) | FR-303 |
| `ringSvg` for majority, no-consensus and no-quorum fixtures: 5 wedges in seat order, fill radius ∝ confidence, abstain wedge empty and labelled, centre text, CLOSE uses the hatch pattern, every wedge has a text label and `aria-label` | FR-304, FR-305, SC-307 |
| Palette constants used by ring, rows, tally and badge; none equal to the P&L green/red or warning yellow | FR-305 |
| `figure_catalog.build` on long call, short put, vertical, iron condor; unavailable figures omitted; display formats per kind | FR-311 (catalog), D-304 |
| `seal`/`unseal` round trip; flipped byte, re-encoded payload, wrong key, 16-min-old, future and NO_QUORUM tokens all raise before any model call | FR-306a, SC-310 |
| Summary route: 503 without key; 422 on extra field or oversize body (values not echoed); 401/502 token paths; 403 on each bad-token case with an identical body; fake model never called in all of these | FR-306a, constitution II |
| Guard: placeholders filled; digit in a bullet removes only that bullet (`trimmed: true`); digit in title or explanation → `unavailable`; unknown placeholder handled like a digit; number word equal to a tally count allowed, other number words not; all bullets dirty → `unavailable` | FR-311, SC-303 |
| Guard: title naming another action, another roll direction, or close/roll under NO_CONSENSUS → `unavailable` | FR-310, SC-302 |
| Summariser prompt: DATA markers with the untrusted label; contains the catalog names and verdict; forbids digits and "what would change"; a rationale containing "ignore previous instructions" stays inside DATA | FR-307, FR-308, FR-309 |
| Fake summariser that sleeps past 10 s → `unavailable` within 15 s | FR-306, SC-304 |
| Vote route returns `summary_token: null` and makes no summary call for NO_QUORUM; client harness shows fixed text and sends no request | FR-313, SC-305 |
| Seat ballot `cited` resolved to catalog chips; unknown and duplicate names dropped; ≤ 5; abstained → `[]` | FR-315 |
| Panel HTML order: badge → warning banner → ring+summary → rows with "Expand all" → collapsed "Research brief & headlines (N)" → disclaimer and data-use notice | FR-316, FR-317 |
| Summary area states: pending "Writing summary…", ok, unavailable, fixed | FR-312, FR-313 |
| Nothing written to sessionStorage/localStorage by the panel (harness storage spy) | FR-318 |
| Privacy scan extended: the summariser request contains no account hash, token, IP or other identifier | FR-314, SC-308 |
| Demo: result has cited figures and a template summary filled from the catalog; no digits typed outside placeholders; no fetch | FR-321 |
| Data-use page lists the summary request | FR-322 |
| `deploy_backend.sh` passes `QUORUM_SEAL_KEY` and warns when missing | D-303 |

## Browser verification (live Schwab + Vertex AI)

1. **Button**: the dashboard shows `ADVICE(Agentic)` with the hazard stripe beside every spread and single-option name; there is no Quorum column. Click it on a collapsed spread: the spread stays collapsed, the graph stays closed, and the panel opens under the row.
2. **Two steps**: in the Network tab, `/api/quorum/vote` resolves and the ring and rows render while the summary area reads "Writing summary…". Then `/api/quorum/summary` resolves and the summary fills in. The vote request body is unchanged from 018. The summary request body contains only `summary_token`.
3. **Ring**: hovering a wedge highlights its row; clicking it, or pressing Tab then Enter, expands the row. Colours are slate HOLD, blue ROLL, hatched orange CLOSE.
4. **Greyscale (SC-307)**: with DevTools rendering set to emulate achromatopsia, every vote is still identifiable from its text label and the hatch.
5. **Summary**: the title matches the verdict, and every number in it also appears in a chip or the fundamentals. There is no "what would change" section.
6. **Tamper**: in DevTools, replay the summary request with one character of the token changed → 403, and the panel shows "Summary unavailable".
7. **No quorum**: force abstentions (e.g. set `QUORUM_MODEL` to an invalid model in a dev instance) → the fixed text shows and no summary request is made.
8. **360 px**: in the device toolbar at 360 px wide, the button is visible without sideways scrolling; the panel stays in view while the table scrolls; the ring stacks above the summary.
9. **Speed (SC-306)**: time click-to-verdict on 5 runs against the 018 build on the same position; the median is not higher. The summary arrives within 15 s of the verdict each time.
10. **Summary quality (SC-309)**: run 10 quorums across at least 3 positions. Every title matches its verdict; at least 8 summaries show in full (`trimmed: false`). Record the tally in the PR.
11. **Demo mode**: the panel shows a demo summary and chips, and the Network tab shows no quorum requests.
12. **Data use page**: lists the summary request to Vertex AI (FR-322).
