Always read .codesight/KNOWLEDGE.md before starting any task if it exists.
Run /clear between sessions.
Model: Sonnet for all tasks unless specified.
NEVER amend `.specify/memory/constitution.md` without asking the user first and getting explicit approval — this includes version bumps, exceptions, and Sync Impact Report edits. If a feature conflicts with the constitution, stop and ask.

<!-- SPECKIT START -->
For context on technologies, project structure, and implementation approach,
read the current plan at `specs/017-macro-quorum-agents/plan.md`. Supporting artifacts:
- `specs/017-macro-quorum-agents/research.md` — decisions D-001–D-008 (ADK per-seat runners, Vertex AI, RSS + search grounding, deterministic tally)
- `specs/017-macro-quorum-agents/data-model.md` — PositionContext, Headline, AnalystBallot/Vote, QuorumResult shapes
- `specs/017-macro-quorum-agents/contracts/quorum-api-contract.md` — POST /api/quorum/vote contract and service APIs
- `specs/017-macro-quorum-agents/quickstart.md` — GCP setup and browser verification protocol
- `specs/017-macro-quorum-agents/spec.md` — feature specification (source of truth)
- `specs/016-t0-payoff-overlay/plan.md` — prior feature (T+0 payoff overlay)
- `.specify/memory/constitution.md` — project constitution v3.2.0
<!-- SPECKIT END -->
