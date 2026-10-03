"""Demo ↔ live mode switch (specs/021): key scoping and switchMode, via a Node harness."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")

HARNESS = Path(__file__).with_name("mode_switch_harness.mjs")
DEMO = {"set_demo": True}
LIVE = {"set_demo": False}


def _run(tmp_path, steps, storage=None) -> dict:
    path = tmp_path / "steps.json"
    path.write_text(json.dumps({"storage": storage or {}, "steps": steps}))
    proc = subprocess.run([NODE, str(HARNESS), str(path)], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _step(module, fn, *args):
    return {"module": module, "fn": fn, "args": list(args)}


class TestScopedKey:
    def test_live_key_unchanged(self, tmp_path):
        out = _run(tmp_path, [LIVE, _step("auth", "scopedKey", "schwab_selected_account")])
        assert out["results"][1] == "schwab_selected_account"

    def test_demo_key_prefixed(self, tmp_path):
        out = _run(tmp_path, [DEMO, _step("auth", "scopedKey", "schwab_selected_account")])
        assert out["results"][1] == "demo:schwab_selected_account"


class TestCacheIsolation:
    """FR-406 / SC-403: each mode reads only its own state."""

    def test_screener_profile_per_mode(self, tmp_path):
        out = _run(tmp_path, [
            LIVE, _step("screener_cache", "saveScreenerProfile", "conservative"),
            DEMO, _step("screener_cache", "loadScreenerProfile"),
            _step("screener_cache", "saveScreenerProfile", "aggressive"),
            LIVE, _step("screener_cache", "loadScreenerProfile"),
            DEMO, _step("screener_cache", "loadScreenerProfile"),
        ])
        r = out["results"]
        assert r[3] == "balanced"
        assert r[6] == "conservative"
        assert r[8] == "aggressive"
        assert out["storage"]["screener_profile"] == "conservative"
        assert out["storage"]["demo:screener_profile"] == "aggressive"

    def test_positions_per_mode(self, tmp_path):
        out = _run(tmp_path, [
            LIVE, _step("position_cache", "savePositions", [{"symbol": "LIVE"}], None),
            DEMO, _step("position_cache", "loadPositions", None),
            _step("position_cache", "savePositions", [{"symbol": "DEMO"}], None),
            LIVE, _step("position_cache", "loadPositions", None),
        ])
        r = out["results"]
        assert r[3] is None
        assert r[6]["positions"] == [{"symbol": "LIVE"}]
        assert "positions" in out["storage"] and "demo:positions" in out["storage"]

    def test_screener_results_per_mode(self, tmp_path):
        out = _run(tmp_path, [
            DEMO, _step("screener_cache", "saveScreenerResults", {"x": 1}, "demo-equity-0002"),
            LIVE, _step("screener_cache", "loadScreenerResults", "demo-equity-0002"),
        ])
        assert out["results"][3] is None
        assert "demo:screener_results_demo-equity-0002" in out["storage"]

    def test_quorum_cache_per_mode(self, tmp_path):
        out = _run(tmp_path, [
            DEMO, _step("quorum_cache", "save", "quorum:v1:SPY|a,b", {"result": "demo"}),
            LIVE, _step("quorum_cache", "load", "quorum:v1:SPY|a,b"),
        ])
        assert "demo:quorum:v1:SPY|a,b" in out["storage"]
        assert "quorum:v1:SPY|a,b" not in out["storage"]

    def test_existing_live_keys_still_read(self, tmp_path):
        """US2-3: a live session saved before this feature keeps working."""
        out = _run(tmp_path, [_step("screener_cache", "loadScreenerProfile")],
                   storage={"screener_profile": "conservative"})
        assert out["results"][0] == "conservative"


class TestSwitchMode:
    def test_to_demo_keeps_token_and_reloads(self, tmp_path):
        out = _run(tmp_path, [_step("auth", "switchMode", "demo", "__location__")],
                   storage={"schwab_access_token": "tok"})
        assert out["storage"]["demo_mode"] == "true"
        assert out["storage"]["schwab_access_token"] == "tok"
        assert out["nav"] == [["reload"]]

    def test_to_live_with_token_reloads_without_oauth(self, tmp_path):
        out = _run(tmp_path, [_step("auth", "switchMode", "live", "__location__")],
                   storage={"schwab_access_token": "tok", "demo_mode": "true", "demo:screener_profile": "aggressive"})
        assert "demo_mode" not in out["storage"]
        assert out["storage"]["demo:screener_profile"] == "aggressive"
        assert out["nav"] == [["reload"]]

    def test_to_live_without_token_starts_oauth(self, tmp_path):
        out = _run(tmp_path, [_step("auth", "switchMode", "live", "__location__")],
                   storage={"demo_mode": "true"})
        assert out["nav"] == [["assign", "/auth/start"]]

    def test_has_live_token(self, tmp_path):
        out = _run(tmp_path, [_step("auth", "hasLiveToken")], storage={"schwab_access_token": "tok"})
        assert out["results"][0] is True
