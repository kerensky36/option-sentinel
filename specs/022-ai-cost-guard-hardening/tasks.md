# Tasks: AI Cost Guard & Deployment Hardening

**Tests**: Required (Constitution IV, Principle II); run and see them fail before implementing.

## Tests (write first, confirm failing)

- [X] T001 [US1] `tests/unit/test_ai_budget.py`: cap default/env/invalid, increment to cap, ET day roll, `seconds_until_reset`, `claim_token` once/expiry purge.
- [X] T002 [US1][US2] `tests/contract/test_quorum_api.py`: 429 `daily_cap` + Retry-After with no model call; rejected requests do not count; cap 0 → 503 `paused` for vote and summary; summary replay → 403 and one summariser call.
- [X] T003 [US1] `tests/unit/test_quorum_ui.py`: daily-cap and paused messages.
- [X] T004 [US3] `tests/unit/test_security_middleware.py` (or new): HTTPS_ONLY + missing/default pepper → startup error.
- [X] T005 [US3][US4] `tests/unit/test_deploy_backend.py`: requires service account; `--service-account`, `--update-secrets`, no secret in env vars, `--max-instances 1`. Dockerfile has non-root `USER`. 004 quickstart has no key/secret prefix. requirements pins python-multipart ≥ 0.0.31.

## Implementation

- [X] T006 [US1][US2] `src/services/ai_budget.py`; wire into `src/api/routes/quorum.py`.
- [X] T007 [US1] `quorum_ui.js` messages.
- [X] T008 [US3] `create_app()` pepper check.
- [X] T009 [US3] `deploy_backend.sh`, `setup_gcp_security.sh`, `.env.example`.
- [X] T010 [US4] Dockerfile, requirements, audit.sh, CI workflows, 004 redaction.
- [X] T011 Quickstart owner checklist; full `pytest -q`; `pip-audit`; `bash -n` on scripts.
