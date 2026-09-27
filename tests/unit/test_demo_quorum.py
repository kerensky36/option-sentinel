"""Tests for the tailored demo quorum (specs/019), run through a Node harness.

frontend/static/js/demo_quorum.js is pure; the harness imports it and prints JSON.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import pytest

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")

HARNESS = Path(__file__).with_name("demo_quorum_harness.mjs")
AS_OF = "2026-09-27T14:00:00Z"
SEAT_IDS = ["greeks_exposure", "volatility_pricing", "time_decay_pnl", "strike_assignment", "macro_news_overlay"]
LENSES = ["Greeks & Exposure", "Volatility & Pricing", "Time Decay & P&L", "Strike & Assignment", "Macro & News Overlay"]


def _leg(**kw) -> dict:
    """A demo-convention leg: signed cost (negative = premium received)."""
    leg = {
        "underlying_symbol": "AAPL", "option_type": "put", "strike": "190.00",
        "expiry_date": "2026-10-30", "days_to_expiry": 33, "quantity": -1,
        "cost": "-3.00", "current_mark": "-2.00", "unrealised_pnl": "100.00",
        "delta": -0.25, "gamma": 0.04, "theta": -0.08, "vega": 0.15,
        "implied_volatility": 0.30, "underlying_price": "200.00", "realised_volatility": 0.24,
    }
    leg.update(kw)
    return leg


def _req(*legs) -> dict:
    return {"as_of": AS_OF, "legs": list(legs) or [_leg()]}


def _run(cases: dict, *, demo_spreads=False, realised_vol=None, tmp_path) -> dict:
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"cases": cases, "demo_spreads": demo_spreads, "realised_vol": realised_vol or {}}))
    proc = subprocess.run([NODE, str(HARNESS), str(path)], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _one(request, tmp_path) -> dict:
    return _run({"x": request}, tmp_path=tmp_path)["cases"]["x"]


def _vote(result, seat):
    return next(v for v in result["votes"] if v["seat"] == seat)


def test_result_shape(tmp_path):
    r = _one(_req(), tmp_path)
    assert [v["seat"] for v in r["votes"]] == SEAT_IDS
    assert [v["lens"] for v in r["votes"]] == LENSES
    assert [t["action"] for t in r["tally"]] == ["CLOSE", "HOLD", "ROLL"]
    assert r["as_of"] == AS_OF
    assert r["underlying_symbol"] == "AAPL"
    assert r["model"] == "demo (no model call)"
    assert r["seats"] == 5 and r["valid_votes"] == 5
    assert r["headlines"] and all(h["title"].startswith("Demo headline") for h in r["headlines"])


def test_verdict_follows_three_of_five_rule(tmp_path):
    for req in (_req(), _req(_leg(days_to_expiry=5)), _req(_leg(unrealised_pnl="250.00"))):
        r = _one(req, tmp_path)
        counts = Counter(v["action"] for v in r["votes"])
        top, n = counts.most_common(1)[0]
        assert r["verdict"] == (top if n >= 3 else "NO_CONSENSUS")
        assert sum(t["votes"] for t in r["tally"]) == 5


def test_greeks_short_near_expiry_rolls(tmp_path):
    v = _vote(_one(_req(_leg(days_to_expiry=5)), tmp_path), "greeks_exposure")
    assert v["action"] == "ROLL" and v["roll_direction"] == "out"
    assert "5 days" in v["rationale"]


def test_greeks_rationale_quotes_net_delta(tmp_path):
    legs = [_leg(delta=-0.25, quantity=-1), _leg(strike="180.00", quantity=1, cost="1.50", delta=0.12)]
    v = _vote(_one(_req(*legs), tmp_path), "greeks_exposure")
    net = round(-0.25 * -1 * 100 + 0.12 * 1 * 100)  # +37
    assert f"{net:+d}" in v["rationale"]


def test_time_decay_takes_profit_when_most_captured(tmp_path):
    # credit 3.00 → max profit $300; pnl $180 → 60 % captured
    v = _vote(_one(_req(_leg(unrealised_pnl="180.00")), tmp_path), "time_decay_pnl")
    assert v["action"] == "CLOSE"
    assert "60%" in v["rationale"]


def test_time_decay_debit_has_no_captured_figure(tmp_path):
    v = _vote(_one(_req(_leg(quantity=1, cost="3.00", unrealised_pnl="-50.00")), tmp_path), "time_decay_pnl")
    assert "max profit" not in v["rationale"]
    assert "33 days" in v["rationale"]


def test_strike_short_call_in_the_money_rolls_up_and_out(tmp_path):
    leg = _leg(option_type="call", strike="195.00", delta=0.62)
    v = _vote(_one(_req(leg), tmp_path), "strike_assignment")
    assert v["action"] == "ROLL" and v["roll_direction"] == "up_and_out"
    assert "2.5%" in v["rationale"]  # (200 − 195) / 200


def test_volatility_unavailable_holds_with_low_confidence(tmp_path):
    v = _vote(_one(_req(_leg(realised_volatility=None)), tmp_path), "volatility_pricing")
    assert v["action"] == "HOLD"
    assert v["confidence"] <= 0.3
    assert "unavailable" in v["rationale"]


def test_volatility_rationale_quotes_iv_rv(tmp_path):
    v = _vote(_one(_req(_leg(implied_volatility=0.36, realised_volatility=0.24)), tmp_path), "volatility_pricing")
    assert "1.50×" in v["rationale"]
    assert v["action"] == "HOLD"  # credit and IV rich


def test_strike_unavailable_without_price(tmp_path):
    v = _vote(_one(_req(_leg(underlying_price=None)), tmp_path), "strike_assignment")
    assert v["action"] == "HOLD" and v["confidence"] <= 0.3
    assert "unavailable" in v["rationale"]


def test_overlay_follows_most_common_fundamentals_vote(tmp_path):
    r = _one(_req(_leg(days_to_expiry=5, unrealised_pnl="180.00")), tmp_path)
    fundamentals = [v["action"] for v in r["votes"][:4]]
    counts = Counter(fundamentals).most_common()
    expected = counts[0][0] if len(counts) == 1 or counts[0][1] > counts[1][1] else "HOLD"
    overlay = _vote(r, "macro_news_overlay")
    assert overlay["action"] == expected
    assert "does not override" in overlay["rationale"]


DEMO_RV = {"AAPL": 0.24, "SPY": 0.15, "TSLA": 0.52, "QQQ": 0.19, "MSFT": 0.21, "AMD": 0.60}


def test_demo_positions_produce_distinct_tallies(tmp_path):
    out = _run({}, demo_spreads=True, realised_vol=DEMO_RV, tmp_path=tmp_path)
    assert len(set(out["demo_tallies"])) >= 2, out["demo_tallies"]


def test_demo_positions_cover_hold_roll_and_close(tmp_path):
    """SC-201: the verdict varies across demo positions."""
    verdicts = _run({}, demo_spreads=True, realised_vol=DEMO_RV, tmp_path=tmp_path)["demo_verdicts"]
    assert {"HOLD", "ROLL", "CLOSE"} <= set(verdicts.values()), verdicts
    assert verdicts["NVDA x1"] == "ROLL"
    assert verdicts["AMD x1"] == "CLOSE"


def test_harness_realised_vol_matches_demo_data(tmp_path):
    js = (Path(__file__).parents[2] / "frontend/static/js/demo_data.js").read_text()
    for sym, rv in DEMO_RV.items():
        assert f"{sym}: {rv}" in js


def test_prob_itm_is_consistent_with_moneyness(tmp_path):
    """In-the-money short leg must not show a < 50 % chance of finishing in the money."""
    import re

    leg = _leg(strike="205.00", delta=-0.24)  # put 2.5 % in the money; demo delta is unrealistic
    v = _vote(_one(_req(leg), tmp_path), "strike_assignment")
    pct = int(re.search(r"≈(\d+)% chance", v["rationale"]).group(1))
    assert pct > 50


# ── specs/020: demo summary via the intercepted summary request (T027) ─────────

UI_HARNESS = Path(__file__).with_name("quorum_ui_harness.mjs")


def _ui(calls, tmp_path):
    path = tmp_path / "ui_calls.json"
    path.write_text(json.dumps({"calls": calls}))
    proc = subprocess.run([NODE, str(UI_HARNESS), str(path)], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _decode_demo(token):
    import base64
    body = token.split(".", 1)[1]
    return json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))


def test_demo_result_carries_demo_token_and_cited_figures(tmp_path):
    r = _one(_req(), tmp_path)
    assert r["summary_token"].startswith("demo.")
    payload = _decode_demo(r["summary_token"])
    assert payload["verdict"] == r["verdict"]
    assert payload["figures"]
    cited = [c for v in r["votes"] for c in v["cited_figures"]]
    assert cited, "demo seats should cite figures"
    for c in cited:
        assert payload["figures"][c["name"]]["display"] == c["display"]
    assert _one({"as_of": AS_OF, "legs": []}, tmp_path)["summary_token"] is None


def test_demo_summary_uses_only_catalog_numbers(tmp_path):
    for req in (_req(), _req(_leg(days_to_expiry=5)), _req(_leg(unrealised_pnl="250.00"))):
        r = _one(req, tmp_path)
        payload = _decode_demo(r["summary_token"])
        out = _ui([{"module": "demo_quorum", "fn": "buildDemoSummary", "args": [payload]}], tmp_path)["results"][0]
        assert out["status"] == "ok"
        s = out["summary"]
        text = " ".join([s["title"], s["explanation"], *s["why"], s["dissent"]])
        for display in sorted((f["display"] for f in payload["figures"].values()), key=len, reverse=True):
            text = text.replace(display, "")
        assert not re.search(r"\d", text), text
        if r["verdict"] in ("CLOSE", "HOLD", "ROLL"):
            assert r["verdict"].lower() in s["title"].lower()
        assert "demo" in s["title"].lower() or "demo" in s["explanation"].lower()


def test_demo_data_answers_summary_without_network(tmp_path):
    r = _one(_req(), tmp_path)
    opts = {"method": "POST", "body": json.dumps({"summary_token": r["summary_token"]})}
    out = _ui([{"module": "demo_data", "fn": "demoResponse", "args": ["/api/quorum/summary", opts]}], tmp_path)
    resp = out["results"][0]
    assert resp["status"] == 200 and resp["json"]["status"] == "ok"
    assert out["fetches"] == []
    bad = _ui([{"module": "demo_data", "fn": "demoResponse",
                "args": ["/api/quorum/summary", {"method": "POST", "body": json.dumps({"summary_token": "x.y"})}]}], tmp_path)
    assert bad["results"][0]["json"]["status"] == "unavailable"
