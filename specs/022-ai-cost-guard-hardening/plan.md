# Implementation Plan: AI Cost Guard & Deployment Hardening

**Branch**: `022-ai-cost-guard-hardening` | **Spec**: [spec.md](./spec.md)

## Design

- `src/services/ai_budget.py` (new, ~60 lines): module-level state behind a `threading.Lock`.
  - `daily_cap()` reads `QUORUM_DAILY_CAP` (default 300; invalid → default + warning).
  - `try_start(now) -> bool`: roll the ET day, compare, increment.
  - `seconds_until_reset(now) -> int`.
  - `claim_token(token_id, expires_at, now) -> bool`: purge expired, reject seen ids.
  - `reset()` for tests.
- `src/api/routes/quorum.py`: paused check (cap 0) first in both routes; cap check after context build in vote; `claim_token(mac, now + MAX_TOKEN_AGE + MAX_SKEW)` after a successful `unseal` in summary.
- `src/api/main.py`: FR-509 check in `create_app()`.
- `frontend/static/js/quorum_ui.js`: on 429/503 read `reason` from the JSON body for the message.
- `scripts/deploy_backend.sh`: FR-507. `scripts/setup_gcp_security.sh`: FR-508.
- `Dockerfile`: `useradd` + `USER app`, `PYTHONDONTWRITEBYTECODE=1`.
- `requirements.txt`: `python-multipart==0.0.32`. `scripts/audit.sh`: drop `--require-hashes`.
- `.github/workflows/ci.yml` (tests + pip-audit); `codeql.yml` adds `javascript-typescript`.
- Docs: `specs/022-…/quickstart.md` owner checklist; redact 004 quickstart.

## Constitution Check

- I Privacy: the counter and used-token set hold no user data (token ids are MACs of server-issued tokens). Memory only. ✅
- II Security: every control has a failing test first (cap, pause, replay, pepper, deploy flags). ✅
- III/IV: spec committed first; tests written and seen failing. ✅
- V Simplicity: one small module; no new dependency. ✅

## Complexity Tracking

None.
