# Quickstart: AI Cost Guard & Deployment Hardening

## Automated checks

```bash
python -m pytest -q tests/unit/test_ai_budget.py tests/contract/test_quorum_api.py \
  tests/unit/test_deploy_backend.py tests/unit/test_setup_gcp_security.py \
  tests/unit/test_security_middleware.py tests/unit/test_quorum_ui.py
bash scripts/audit.sh          # pip-audit: expect "No known vulnerabilities found"
```

## Owner checklist (do these in order)

1. **Rotate the Schwab app secret.** The first 12 characters of the app key and
   secret are in git history (`specs/004-…/quickstart.md`, commits `1ad94fc`,
   `18e1b8f`). Regenerate the secret in the Schwab developer portal and put the new
   value in `.env` as `SCHWAB_CLIENT_SECRET`.

2. **Run the one-time setup** (creates `option-sentinel-run`, the three secrets, and
   moves the live service onto them):

   ```bash
   bash scripts/setup_gcp_security.sh            # first time
   bash scripts/setup_gcp_security.sh --rotate   # later, after rotating a secret
   ```

   Then add `CLOUD_RUN_SERVICE_ACCOUNT=option-sentinel-run@<project>.iam.gserviceaccount.com`
   to `.env`. `deploy_backend.sh` refuses to run without it.

3. **Take Vertex AI away from the Compute default account** (the setup script prints
   the exact command). Also review whether that account still has project Editor.

4. **Budget with a hard stop.** A budget alone only emails; it does not stop spend.
   - Create the budget (the setup script does this when `BILLING_ACCOUNT_ID` is set),
     and connect it to a Pub/Sub topic: Billing → Budgets & alerts → the budget →
     *Connect a Pub/Sub topic*.
   - Subscribe a small Cloud Run function to the topic that, when
     `costAmount >= budgetAmount`, either sets `QUORUM_DAILY_CAP=0` on the service
     (pauses AI only) or disables billing for the project (stops everything). Google's
     "Disable billing usage with notifications" guide has the reference function.

5. **Cap Vertex AI quota.** IAM & Admin → Quotas & system limits → filter
   `aiplatform.googleapis.com` and the Gemini model you use → lower the per-minute
   request quota to what one user needs (each analysis is 6–7 requests).

6. **Pin the base image by digest** (needs Docker Hub access):

   ```bash
   docker buildx imagetools inspect python:3.13-slim --format '{{json .Manifest.Digest}}'
   # then in Dockerfile: FROM python:3.13-slim@sha256:<digest>
   ```

## Tuning

| Env var | Default | Effect |
|---|---|---|
| `QUORUM_DAILY_CAP` | 50 | AI analyses per America/New_York day for the whole service. 0 pauses every AI route (503 `paused`). |
| `CLOUD_RUN_CONCURRENCY` | 10 | Requests the single instance handles at once. |
| `CLOUD_RUN_TIMEOUT` | 90 | Seconds before Cloud Run ends a request. |

One analysis = one ADVICE(Agentic) click without a saved result (5 votes + research + summary,
about 7 Gemini calls). At ~2.5¢ per analysis on Gemini 2.5 Flash, 50/day ≈ $1.25/day worst
case per instance-day. A restart resets the count, so keep the budget stop (step 4) and the
Vertex AI quota (step 5, ~30 requests/minute).

## Browser check

With `QUORUM_DAILY_CAP=1` locally: the first ADVICE(Agentic) click works; the second
shows "Today's AI analysis limit has been reached — it resets at midnight ET."
With `QUORUM_DAILY_CAP=0`: "AI analysis is paused on this server."
