"""Deterministic quorum tally (specs/017 FR-007, research D-005).

Pure function — the verdict is arithmetic over the seats' ballots, never a
model decision, so headline prompt-injection cannot sway the count.
"""
from __future__ import annotations

from src.data.models import AnalystVote, QuorumVerdict, TallyEntry

QUORUM_SEATS = 5
QUORUM_MIN_VALID = 3
MAJORITY_VOTES = 3  # strict majority of the five seats

_ACTIONS = ("CLOSE", "HOLD", "ROLL")


def tally_votes(
    votes: list[AnalystVote],
) -> tuple[QuorumVerdict, bool, int, list[TallyEntry]]:
    """Return (verdict, quorum_met, valid_votes, tally) for the given seat votes."""
    valid = [v for v in votes if not v.abstained and v.action is not None]

    tally: list[TallyEntry] = []
    for action in _ACTIONS:
        chosen = [v for v in valid if v.action == action]
        confidences = [v.confidence for v in chosen if v.confidence is not None]
        tally.append(
            TallyEntry(
                action=action,
                votes=len(chosen),
                mean_confidence=sum(confidences) / len(confidences) if confidences else None,
            )
        )

    quorum_met = len(valid) >= QUORUM_MIN_VALID
    if not quorum_met:
        verdict: QuorumVerdict = "NO_QUORUM"
    else:
        winners = [t.action for t in tally if t.votes >= MAJORITY_VOTES]
        verdict = winners[0] if winners else "NO_CONSENSUS"

    return verdict, quorum_met, len(valid), tally
