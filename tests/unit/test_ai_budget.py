"""Global daily AI cap and single-use summary tokens (specs/022 FR-501–FR-505)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.services import ai_budget

# 2026-10-05 14:00 UTC = 10:00 America/New_York (EDT)
NOON = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.delenv("QUORUM_DAILY_CAP", raising=False)
    ai_budget.reset()
    yield
    ai_budget.reset()


class TestDailyCap:
    def test_default_cap_is_300(self):
        assert ai_budget.daily_cap() == 300

    def test_cap_from_env(self, monkeypatch):
        monkeypatch.setenv("QUORUM_DAILY_CAP", "25")
        assert ai_budget.daily_cap() == 25

    @pytest.mark.parametrize("bad", ["abc", "-1", "1.5", ""])
    def test_invalid_cap_falls_back_to_default(self, monkeypatch, bad):
        monkeypatch.setenv("QUORUM_DAILY_CAP", bad)
        assert ai_budget.daily_cap() == 300

    def test_zero_means_paused(self, monkeypatch):
        monkeypatch.setenv("QUORUM_DAILY_CAP", "0")
        assert ai_budget.paused() is True
        monkeypatch.setenv("QUORUM_DAILY_CAP", "3")
        assert ai_budget.paused() is False

    def test_counts_up_to_cap_then_refuses(self, monkeypatch):
        monkeypatch.setenv("QUORUM_DAILY_CAP", "2")
        assert ai_budget.try_start(NOON) is True
        assert ai_budget.try_start(NOON) is True
        assert ai_budget.try_start(NOON) is False
        assert ai_budget.try_start(NOON) is False
        assert ai_budget.used_today(NOON) == 2

    def test_new_new_york_day_resets(self, monkeypatch):
        monkeypatch.setenv("QUORUM_DAILY_CAP", "1")
        late = datetime(2026, 10, 6, 3, 59, tzinfo=timezone.utc)   # 23:59 ET on the 5th
        after = datetime(2026, 10, 6, 4, 0, tzinfo=timezone.utc)   # 00:00 ET on the 6th
        assert ai_budget.try_start(NOON) is True
        assert ai_budget.try_start(late) is False
        assert ai_budget.try_start(after) is True

    def test_seconds_until_reset_is_next_et_midnight(self):
        assert ai_budget.seconds_until_reset(NOON) == 14 * 3600
        just_before = datetime(2026, 10, 6, 3, 59, 30, tzinfo=timezone.utc)
        assert ai_budget.seconds_until_reset(just_before) == 30


class TestSummaryTokens:
    def test_token_claimed_once(self):
        exp = NOON + timedelta(minutes=17)
        assert ai_budget.claim_token("mac-1", exp, NOON) is True
        assert ai_budget.claim_token("mac-1", exp, NOON) is False
        assert ai_budget.claim_token("mac-2", exp, NOON) is True

    def test_expired_records_are_purged(self):
        exp = NOON + timedelta(minutes=17)
        ai_budget.claim_token("mac-1", exp, NOON)
        later = exp + timedelta(seconds=1)
        ai_budget.claim_token("mac-2", later + timedelta(minutes=17), later)
        assert ai_budget.tracked_tokens() == 1
