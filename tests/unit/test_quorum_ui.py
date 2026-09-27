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
