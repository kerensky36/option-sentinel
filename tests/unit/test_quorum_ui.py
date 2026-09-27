"""Tests for the advice panel UI modules (specs/020), run through a Node harness.

quorum_ring.js, quorum_ui.js (pure exports) and positions_rows.js are exercised
without a browser: the harness imports them and prints JSON results.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")

HARNESS = Path(__file__).with_name("quorum_ui_harness.mjs")
ROOT = Path(__file__).resolve().parents[2]
JS = ROOT / "frontend" / "static" / "js"

SEAT_IDS = ["greeks_exposure", "volatility_pricing", "time_decay_pnl", "strike_assignment", "macro_news_overlay"]
LENSES = ["Greeks & Exposure", "Volatility & Pricing", "Time Decay & P&L", "Strike & Assignment", "Macro & News Overlay"]


def _vote(i, action, confidence=None, roll=None, cited=None, rationale=None):
    abstained = action is None
    return {
        "seat": SEAT_IDS[i],
        "lens": LENSES[i],
        "action": action,
        "confidence": confidence,
        "rationale": rationale if rationale is not None else ("" if abstained else f"Reason {i} <b>bold</b>"),
        "roll_direction": roll,
        "abstained": abstained,
        "cited_figures": cited or [],
    }


def _tally(votes):
    out = []
    for action in ("CLOSE", "HOLD", "ROLL"):
        chosen = [v for v in votes if v["action"] == action]
        mean = sum(v["confidence"] for v in chosen) / len(chosen) if chosen else None
        out.append({"action": action, "votes": len(chosen), "mean_confidence": mean})
    return out


def _result(votes, verdict, token="tok.en"):
    valid = sum(1 for v in votes if not v["abstained"])
    return {
        "verdict": verdict,
        "quorum_met": valid >= 3,
        "seats": 5,
        "valid_votes": valid,
        "tally": _tally(votes),
        "votes": votes,
        "macro_brief": "Jobs report <Oct 2> falls inside the window.",
        "headlines": [
            {"publisher": "CNBC", "title": "Fed <holds>", "link": "https://www.cnbc.com/a", "published": None, "summary": ""},
            {"publisher": "Bloomberg", "title": "Yields drift", "link": "javascript:alert(1)", "published": None, "summary": ""},
        ],
        "underlying_symbol": "SPY",
        "model": "gemini-2.5-flash",
        "generated_at": "2026-09-27T14:40:00Z",
        "as_of": "2026-09-27T14:30:00Z",
        "position_fundamentals": {"breakevens": [563.55]},
        "disclaimer": "Informational only — not financial advice. Option Sentinel never places trades.",
        "summary_token": token if verdict != "NO_QUORUM" else None,
    }


CITED = [{"name": "leg1_iv_rv", "label": "IV/RV", "display": "1.08×"}]

RESULT_MAJORITY = _result(
    [
        _vote(0, "HOLD", 0.55),
        _vote(1, "HOLD", 0.50, cited=CITED),
        _vote(2, "ROLL", 0.60, "out"),
        _vote(3, "ROLL", 0.60, "out"),
        _vote(4, "ROLL", 0.55, "out"),
    ],
    "ROLL",
)
RESULT_SPLIT = _result(
    [
        _vote(0, "HOLD", 0.55),
        _vote(1, "CLOSE", 0.55),
        _vote(2, "ROLL", 0.60, "out"),
        _vote(3, "ROLL", 0.60, "up_and_out"),
        _vote(4, "HOLD", 0.50),
    ],
    "NO_CONSENSUS",
)
RESULT_NO_QUORUM = _result(
    [_vote(0, "HOLD", 0.55), _vote(1, None), _vote(2, "ROLL", 0.60, "out"), _vote(3, None), _vote(4, None)],
    "NO_QUORUM",
)
RESULT_MIXED_ROLL = _result(
    [
        _vote(0, "ROLL", 0.6, "out"),
        _vote(1, "ROLL", 0.6, "up_and_out"),
        _vote(2, "ROLL", 0.6, "out"),
        _vote(3, "HOLD", 0.5),
        _vote(4, "HOLD", 0.5),
    ],
    "ROLL",
)


def _run_calls(calls, tmp_path) -> dict:
    path = tmp_path / "calls.json"
    path.write_text(json.dumps({"calls": calls}))
    proc = subprocess.run([NODE, str(HARNESS), str(path)], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _call(tmp_path, module, fn, *args):
    return _run_calls([{"module": module, "fn": fn, "args": list(args)}], tmp_path)["results"][0]


# ── US1: ADVICE(Agentic) button and placement (FR-301–FR-303) ──────────────────

def _pos(symbol, strike, qty, option_type="put", expiry="2026-10-09", underlying="SPY"):
    return {
        "symbol": symbol, "underlying_symbol": underlying, "option_type": option_type,
        "strike": strike, "expiry_date": expiry, "days_to_expiry": 12, "quantity": qty,
        "current_mark": "1.55", "unrealised_pnl": "55.00", "cost": "2.10",
        "delta": 0.31, "gamma": -0.02, "theta": 0.15, "vega": -0.42, "implied_volatility": 0.162,
        "delta_source": "schwab", "gamma_source": "schwab", "theta_source": "schwab",
        "vega_source": "schwab", "iv_source": "schwab", "underlying_price": "572.40",
    }


def test_advice_button_html(tmp_path):
    html = _call(tmp_path, "quorum_ui", "adviceButton", "SPY-grp")
    text = re.sub(r"<[^>]+>", "", html).strip()
    assert text.replace("⚠", "").strip() == "ADVICE(Agentic)"
    assert 'class="hazard"' in html
    assert 'data-quorum-btn="SPY-grp"' in html
    assert 'aria-describedby="advice-warning-note"' in html
    note = _call(tmp_path, "quorum_ui", "adviceWarningNote")
    assert 'id="advice-warning-note"' in note
    assert "AI opinion" in note and "not financial advice" in note.lower()


def test_advice_button_escapes_id(tmp_path):
    html = _call(tmp_path, "quorum_ui", "adviceButton", '<x">')
    assert "<x" not in html.split("data-quorum-btn=")[1].split(">")[0]
    assert "&lt;x&quot;&gt;" in html


def test_table_has_no_quorum_column_and_fourteen_headers(tmp_path):
    header = _call(tmp_path, "positions_rows", "tableHeader")
    ths = re.findall(r"<th[^>]*>(.*?)</th>", header, re.S)
    assert len(ths) == 14
    assert not any("Quorum" in t for t in ths)


def test_standalone_row_has_one_button_in_first_cell(tmp_path):
    row = _call(tmp_path, "positions_rows", "standaloneRow", _pos("SPY 261016C590", "590.00", 2, "call"))
    first_td = re.search(r"<td[^>]*>(.*?)</td>", row, re.S).group(1)
    assert row.count("ADVICE(Agentic)") == 1
    assert "ADVICE(Agentic)" in first_td
    assert first_td.index("SPY 261016C590") < first_td.index("ADVICE(Agentic)")
    assert len(re.findall(r"<td", row)) == 14


def test_spread_rows_button_on_summary_only(tmp_path):
    group = {
        "groupId": "SPY%7C2026-10-09", "groupName": "SPY · 2026-10-09", "underlying": "SPY",
        "expiry": "2026-10-09",
        "legs": [_pos("SPY 261009P565", "565.00", -1), _pos("SPY 261009P560", "560.00", 1)],
    }
    html = _call(tmp_path, "positions_rows", "spreadRows", group)
    rows = re.findall(r"<tr.*?</tr>", html, re.S)
    assert len(rows) == 3
    summary, *legs = rows
    assert summary.count("ADVICE(Agentic)") == 1
    first_td = re.search(r"<td[^>]*>(.*?)</td>", summary, re.S).group(1)
    assert "ADVICE(Agentic)" in first_td
    assert 'data-quorum-btn="SPY%7C2026-10-09"' in summary
    for leg in legs:
        assert "ADVICE(Agentic)" not in leg
        assert len(re.findall(r"<td", leg)) == 14
    assert len(re.findall(r"<td", summary)) == 14


def test_panel_and_graph_rows_span_fourteen_columns():
    assert "colspan=\"${COLSPAN}\"" in (JS / "quorum_ui.js").read_text()
    assert re.search(r"const COLSPAN = 14;", (JS / "quorum_ui.js").read_text())
    graph = (JS / "payoff_graph.js").read_text()
    assert 'colspan="14"' in graph and 'colspan="15"' not in graph


def test_click_on_advice_button_stops_propagation(tmp_path):
    out = _call(tmp_path, "quorum_ui", "onTableClick",
                {"__event__": {"matches": ["[data-quorum-btn]"], "id": "SPY-grp"}}, {"__const__": None})
    assert out["value"] is True
    assert out["logs"][0]["stopped"] is True


def test_click_elsewhere_is_ignored(tmp_path):
    out = _call(tmp_path, "quorum_ui", "onTableClick",
                {"__event__": {"matches": ["[data-spread-toggle]"], "id": "x"}}, {"__const__": None})
    assert out["value"] is False
    assert out["logs"][0]["stopped"] is False


def test_closing_panels_only_touches_quorum_rows(tmp_path):
    out = _call(tmp_path, "quorum_ui", "closeQuorumPanel", {"__fake_root__": True})
    assert out["logs"][0] == [".quorum-panel-row"]


# ── US2: radial vote ring, palette, panel header (FR-304, FR-305, FR-316, FR-317) ──

PALETTE = {"CLOSE": "#e8703a", "HOLD": "#8c93a8", "ROLL": "#3aa8e0", "NONE": "#3a3a4a"}


def _wedges(svg):
    return re.findall(r'<g class="wedge"(.*?)</g>', svg, re.S)


def _centre(svg):
    return " ".join(re.findall(r'<text[^>]*class="centre[^"]*"[^>]*>(.*?)</text>', svg))


@pytest.mark.parametrize("result", [RESULT_MAJORITY, RESULT_SPLIT, RESULT_NO_QUORUM])
def test_ring_has_five_accessible_wedges_in_seat_order(tmp_path, result):
    svg = _call(tmp_path, "quorum_ring", "ringSvg", result)
    wedges = _wedges(svg)
    assert len(wedges) == 5
    assert re.findall(r'<g class="wedge" data-seat="([a-z_]+)"', svg) == SEAT_IDS
    for w, v in zip(wedges, result["votes"]):
        assert 'tabindex="0"' in w and 'role="button"' in w
        label = re.search(r'aria-label="([^"]*)"', w).group(1)
        assert v["lens"].replace("&", "&amp;") in label
        if v["abstained"]:
            assert "abstained" in label
            assert "ABSTAIN" in w
            assert PALETTE["NONE"] in w
        else:
            assert v["action"] in label and f"{round(v['confidence'] * 100)}%" in label
            assert v["action"] in re.sub(r"<[^>]+>", " ", w)  # visible text label (SC-307)
            radius = float(re.search(r'class="wedge-fill[^"]*"[^>]*d="M[^A]*A([\d.]+),', w).group(1))
            assert abs(radius - (50 + 54 * v["confidence"])) <= 0.5
            band = re.search(r'class="wedge-band"[^>]*fill="([^"]+)"', w).group(1)
            assert band == PALETTE[v["action"]]


def test_ring_close_uses_hatch_and_roll_labels_show_direction(tmp_path):
    svg = _call(tmp_path, "quorum_ring", "ringSvg", RESULT_SPLIT)
    assert '<pattern id="hatch"' in svg
    close_wedge = _wedges(svg)[1]
    assert 'fill="url(#hatch)"' in close_wedge
    assert "ROLL out" in _wedges(svg)[2]
    assert "ROLL up &amp; out" in _wedges(svg)[3]


def test_ring_centre_text(tmp_path):
    assert _centre(_call(tmp_path, "quorum_ring", "ringSvg", RESULT_MAJORITY)) == "ROLL OUT 3 of 5"
    assert _centre(_call(tmp_path, "quorum_ring", "ringSvg", RESULT_SPLIT)) == "NO CONSENSUS 5 of 5 voted"
    assert _centre(_call(tmp_path, "quorum_ring", "ringSvg", RESULT_NO_QUORUM)) == "NO QUORUM 2 of 5 voted"
    assert _centre(_call(tmp_path, "quorum_ring", "ringSvg", RESULT_MIXED_ROLL)) == "ROLL 3 of 5"


def test_vote_palette_constants(tmp_path):
    out = _call(tmp_path, "quorum_ring", "VOTE_COLORS")
    assert out["__value__"] == PALETTE


def test_vote_palette_avoids_pnl_and_warning_colours():
    base = (ROOT / "frontend" / "templates" / "base.html").read_text().lower()
    for reserved in ("#2ec82e", "#48d848", "#d43c3c", "#e05050", "#c8a820", "#d4b840"):
        assert reserved not in {c.lower() for c in PALETTE.values()}
        assert reserved in base  # still the app's P&L / warning colours
    ui = (JS / "quorum_ui.js").read_text()
    assert "ACTION_BAR" not in ui and "#b33" not in ui and "#56c" not in ui


def _panel(tmp_path, result):
    return _call(tmp_path, "quorum_ui", "renderResult", result)


def test_panel_header_order_and_warning_banner(tmp_path):
    html = _panel(tmp_path, RESULT_MAJORITY)
    order = [
        html.index('class="verdict"'),
        html.index("3 of 5 analysts agree"),
        html.index("Data as of"),
        html.index("AI-generated opinion. Not financial advice. Option Sentinel never places trades."),
        html.index("<svg"),
    ]
    assert order == sorted(order)
    assert re.search(r'class="verdict"[^>]*>ROLL OUT<', html)


def test_panel_header_notes_for_split_and_no_quorum(tmp_path):
    split = _panel(tmp_path, RESULT_SPLIT)
    assert re.search(r'class="verdict"[^>]*>NO CONSENSUS<', split)
    assert "No action reached a 3-of-5 majority" in split
    nq = _panel(tmp_path, RESULT_NO_QUORUM)
    assert re.search(r'class="verdict"[^>]*>NO QUORUM<', nq)
    assert "Only 2 of 5 analysts voted" in nq


def test_tally_lists_counts_and_marks_the_winner(tmp_path):
    html = _panel(tmp_path, RESULT_MAJORITY)
    tally = re.search(r'<div class="tally[^"]*">(.*?)</div>', html, re.S).group(1)
    text = re.sub(r"<[^>]+>", " ", tally)
    assert "CLOSE 0" in text and "HOLD 2" in text and "ROLL 3" in text
    assert "ABSTAIN" not in text
    assert re.search(r'class="win"[^>]*>.*?ROLL 3', tally, re.S)
    nq = re.search(r'<div class="tally[^"]*">(.*?)</div>', _panel(tmp_path, RESULT_NO_QUORUM), re.S).group(1)
    assert "ABSTAIN 3" in re.sub(r"<[^>]+>", " ", nq)


def test_panel_escapes_model_and_feed_text(tmp_path):
    html = _panel(tmp_path, RESULT_MAJORITY)
    assert "<b>bold</b>" not in html and "&lt;b&gt;bold&lt;/b&gt;" in html
    assert "Fed <holds>" not in html and "Fed &lt;holds&gt;" in html
    assert "javascript:" not in html


# ── US3: summary area and the second request (FR-306, FR-309, FR-312, FR-313) ──

SUMMARY = {
    "title": "Roll the spread out <now>.",
    "explanation": "It banked 38% of $86.",
    "why": ["Time decay: 38% captured.", "Strike: close to spot."],
    "dissent": "Greeks and Volatility would hold.",
}


def test_summary_area_states(tmp_path):
    pending = _call(tmp_path, "quorum_ui", "renderSummary", "pending", None, RESULT_MAJORITY)
    assert "Writing summary…" in pending
    unavailable = _call(tmp_path, "quorum_ui", "renderSummary", "unavailable", None, RESULT_MAJORITY)
    assert "Summary unavailable" in unavailable
    fixed = _call(tmp_path, "quorum_ui", "renderSummary", "fixed", None, RESULT_NO_QUORUM)
    assert "Only 2 of 5 analysts voted — no recommendation." in fixed


def test_summary_ok_layout_and_escaping(tmp_path):
    html = _call(tmp_path, "quorum_ui", "renderSummary", "ok", SUMMARY, RESULT_MAJORITY)
    assert re.search(r"<h2[^>]*>Roll the spread out &lt;now&gt;\.</h2>", html)
    assert "<now>" not in html
    assert "Why the majority" in html and "Where the votes fell" not in html
    assert html.count("<li>") == 2
    assert "Dissent" in html and "Greeks and Volatility would hold." in html
    assert "LLM-written" in html
    assert "What would change" not in html and "what would change" not in html
    split = _call(tmp_path, "quorum_ui", "renderSummary", "ok", SUMMARY, RESULT_SPLIT)
    assert "Where the votes fell" in split and "Why the majority" not in split


def test_panel_starts_with_summary_area_state(tmp_path):
    assert 'data-state="pending"' in _call(tmp_path, "quorum_ui", "renderResult", RESULT_MAJORITY)
    assert 'data-state="fixed"' in _call(tmp_path, "quorum_ui", "renderResult", RESULT_NO_QUORUM)
    no_token = dict(RESULT_MAJORITY, summary_token=None)
    assert 'data-state="unavailable"' in _call(tmp_path, "quorum_ui", "renderResult", no_token)


def _request_summary(tmp_path, result, fetch_spec, current=True, timeout_ms=20000):
    out = _run_calls([{
        "module": "quorum_ui", "fn": "requestSummary", "async": True,
        "args": [result, {"__fake_fetch__": fetch_spec}, {"__const__": current}, timeout_ms],
    }], tmp_path)
    return out["results"][0], out["fetches"], out["storage_writes"]


def test_no_quorum_sends_no_request(tmp_path):
    value, fetches, _ = _request_summary(tmp_path, RESULT_NO_QUORUM, {"status": 200, "body": {}})
    assert value == {"state": "fixed", "summary": None}
    assert fetches == []


def test_missing_token_sends_no_request(tmp_path):
    value, fetches, _ = _request_summary(tmp_path, dict(RESULT_MAJORITY, summary_token=None), {"status": 200, "body": {}})
    assert value == {"state": "unavailable", "summary": None}
    assert fetches == []


def test_token_is_posted_once_and_ok_rendered(tmp_path):
    body = {"status": "ok", "trimmed": False, "summary": SUMMARY}
    value, fetches, writes = _request_summary(tmp_path, RESULT_MAJORITY, {"status": 200, "body": body})
    assert value == {"state": "ok", "summary": SUMMARY}
    assert fetches == [{"url": "/api/quorum/summary", "body": {"summary_token": "tok.en"}}]
    assert writes == []  # FR-318: nothing stored


@pytest.mark.parametrize("spec", [
    {"status": 403, "body": {"detail": "Summary request rejected"}},
    {"status": 200, "body": {"status": "unavailable", "trimmed": False, "summary": None}},
    {"throw": True, "status": 0, "body": None},
    {"hang": True, "status": 0, "body": None},
])
def test_failures_become_unavailable(tmp_path, spec):
    value, fetches, _ = _request_summary(tmp_path, RESULT_MAJORITY, spec, timeout_ms=50)
    assert value == {"state": "unavailable", "summary": None}
    assert len(fetches) == 1


def test_stale_panel_is_not_updated(tmp_path):
    body = {"status": "ok", "trimmed": False, "summary": SUMMARY}
    value, _, _ = _request_summary(tmp_path, RESULT_MAJORITY, {"status": 200, "body": body}, current=False)
    assert value is None


# ── US4: analyst rows, expand all, brief section (FR-315, FR-316, FR-320) ──────

def _members(html):
    return re.findall(r'<details class="member"[^>]*data-seat="([a-z_]+)"[^>]*>(.*?)</details>', html, re.S)


def test_five_collapsed_rows_in_seat_order(tmp_path):
    html = _panel(tmp_path, RESULT_SPLIT)
    rows = _members(html)
    assert [seat for seat, _ in rows] == SEAT_IDS
    assert not re.search(r'<details class="member"[^>]*\bopen\b', html)
    for (seat, body), v in zip(rows, RESULT_SPLIT["votes"]):
        summary = re.search(r"<summary>(.*?)</summary>", body, re.S).group(1)
        assert PALETTE[v["action"]] in summary  # stripe colour
        assert v["lens"].replace("&", "&amp;") in summary
        assert f">{v['action']}<" in summary
        pct = round(v["confidence"] * 100)
        assert f"width:{pct}%" in summary and f"{pct}%" in re.sub(r"<[^>]+>", " ", summary)
    roll = dict(rows)["strike_assignment"]
    assert "roll up &amp; out" in roll


def test_abstained_row(tmp_path):
    rows = dict(_members(_panel(tmp_path, RESULT_NO_QUORUM)))
    summary = re.search(r"<summary>(.*?)</summary>", rows["volatility_pricing"], re.S).group(1)
    assert ">ABSTAINED<" in summary and "—" in summary and PALETTE["NONE"] in summary


def test_row_body_has_rationale_and_figure_chips(tmp_path):
    rows = dict(_members(_panel(tmp_path, RESULT_MAJORITY)))
    body = rows["volatility_pricing"]
    assert "&lt;b&gt;bold&lt;/b&gt;" in body
    chips = re.findall(r'<span class="fig">(.*?)</span>\s*(?=<span class="fig">|</div>)', body, re.S)
    assert len(chips) == 1 and "IV/RV" in chips[0] and "1.08×" in chips[0]
    assert '<span class="fig">' not in rows["greeks_exposure"]


def test_expand_all_control_and_collapsed_brief(tmp_path):
    html = _panel(tmp_path, RESULT_MAJORITY)
    assert re.search(r'<button[^>]*class="toggle-all"[^>]*>Expand all</button>', html)
    extra = re.search(r'<details class="extra">(.*?)</details>', html, re.S)
    assert extra and "<details class=\"extra\" open" not in html
    assert "Research brief &amp; headlines (2)" in extra.group(1)
    assert "Jobs report &lt;Oct 2&gt;" in extra.group(1)
    assert 'href="https://www.cnbc.com/a" target="_blank" rel="noopener noreferrer"' in extra.group(1)
    assert "javascript:" not in extra.group(1)


def test_toggle_all_helper(tmp_path):
    out = _run_calls([
        {"module": "quorum_ui", "fn": "toggleAll", "args": [[{"open": False}, {"open": True}]]},
        {"module": "quorum_ui", "fn": "toggleAll", "args": [[{"open": True}, {"open": True}]]},
    ], tmp_path)["results"]
    assert out == ["Collapse all", "Expand all"]


def test_panel_section_order(tmp_path):
    html = _panel(tmp_path, RESULT_MAJORITY)
    order = [html.index("<svg"), html.index('class="summary-area"'), html.index('<details class="member"'),
             html.index('<details class="extra">'), html.index("How we use your data")]
    assert order == sorted(order)
