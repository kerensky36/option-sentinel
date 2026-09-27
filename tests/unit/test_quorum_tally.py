"""Tests for the deterministic quorum tally (specs/017 FR-007, SC-002)."""
from __future__ import annotations

import itertools
from collections import Counter

import pytest

from src.data.models import AnalystVote
from src.services.quorum_tally import tally_votes

_OUTCOMES = ("CLOSE", "HOLD", "ROLL", None)  # None = abstained


def _votes(*actions, confidence: float = 0.5) -> list[AnalystVote]:
    return [
        AnalystVote(
            seat=f"s{i}",
            lens=f"Lens {i}",
            action=a,
            confidence=None if a is None else confidence,
            roll_direction="out" if a == "ROLL" else None,
            abstained=a is None,
        )
        for i, a in enumerate(actions)
    ]


class TestSpecScenarios:
    def test_strict_majority_wins(self):
        verdict, quorum_met, valid, _ = tally_votes(_votes("ROLL", "ROLL", "ROLL", "HOLD", "CLOSE"))
        assert verdict == "ROLL"
        assert quorum_met is True
        assert valid == 5

    def test_two_two_one_is_no_consensus(self):
        verdict, quorum_met, _, _ = tally_votes(_votes("ROLL", "ROLL", "HOLD", "HOLD", "CLOSE"))
        assert verdict == "NO_CONSENSUS"
        assert quorum_met is True

    def test_two_valid_votes_is_no_quorum(self):
        verdict, quorum_met, valid, _ = tally_votes(_votes("ROLL", "ROLL", None, None, None))
        assert verdict == "NO_QUORUM"
        assert quorum_met is False
        assert valid == 2

    def test_three_valid_unanimous_meets_quorum(self):
        verdict, _, _, _ = tally_votes(_votes("CLOSE", "CLOSE", "CLOSE", None, None))
        assert verdict == "CLOSE"


class TestTallyShape:
    def test_tally_always_lists_all_actions_in_order(self):
        _, _, _, tally = tally_votes(_votes("HOLD", None, None, None, None))
        assert [t.action for t in tally] == ["CLOSE", "HOLD", "ROLL"]

    def test_mean_confidence_per_action(self):
        votes = _votes("HOLD", "HOLD", "CLOSE", None, None)
        votes[0].confidence = 0.2
        votes[1].confidence = 0.6
        votes[2].confidence = 0.9
        _, _, _, tally = tally_votes(votes)
        by = {t.action: t for t in tally}
        assert by["HOLD"].votes == 2
        assert by["HOLD"].mean_confidence == pytest.approx(0.4)
        assert by["CLOSE"].mean_confidence == pytest.approx(0.9)
        assert by["ROLL"].votes == 0
        assert by["ROLL"].mean_confidence is None


@pytest.mark.parametrize("combo", list(itertools.product(_OUTCOMES, repeat=5)))
def test_exhaustive_rule(combo):
    """All 4^5 seat outcomes match the FR-007 rule (SC-002)."""
    verdict, quorum_met, valid, tally = tally_votes(_votes(*combo))
    cast = [a for a in combo if a is not None]
    counts = Counter(cast)
    assert valid == len(cast)
    assert sum(t.votes for t in tally) == valid
    assert quorum_met == (len(cast) >= 3)
    if len(cast) < 3:
        expected = "NO_QUORUM"
    else:
        winners = [a for a, n in counts.items() if n >= 3]
        expected = winners[0] if winners else "NO_CONSENSUS"
    assert verdict == expected
