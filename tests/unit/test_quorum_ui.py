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
