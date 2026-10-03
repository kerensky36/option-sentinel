#!/usr/bin/env bash
set -euo pipefail

# Deploy the Option Sentinel backend to GCP Cloud Run.
# Usage: bash scripts/deploy_backend.sh
#
# Required env vars:
#   GCP_PROJECT_ID, SCHWAB_CLIENT_ID, SCHWAB_REDIRECT_URI, SCHWAB_AUTH_URL, SCHWAB_TOKEN_URL
#   CLOUD_RUN_SERVICE_ACCOUNT  (specs/022: dedicated least-privilege runtime account,
#                               created by scripts/setup_gcp_security.sh)
#
# Secrets (specs/022 FR-507) are mounted from Secret Manager, never passed as values:
#   SCHWAB_CLIENT_SECRET <- schwab-client-secret, QUORUM_SEAL_KEY <- quorum-seal-key,
#   LOG_PEPPER <- log-pepper. Create them once with scripts/setup_gcp_security.sh.
#
# Optional env vars (defaults shown):
#   CLOUD_RUN_SERVICE=option-sentinel
#   CLOUD_RUN_REGION=us-central1
#   RISK_FREE_RATE=0.045
#   HTTPS_ONLY=true     (set HSTS header; default true in prod)
#   DEBUG=false         (suppress stack traces; default false in prod)
#   ALLOWED_ORIGIN      (CORS allowed origin; defaults to Firebase hosting URL)
#   QUORUM_DAILY_CAP    (specs/022: AI analyses per day for the whole service; app
#                        default 50; 0 pauses all AI routes)
#   CLOUD_RUN_CONCURRENCY=10  (specs/022 FR-514: requests handled at once)
#   CLOUD_RUN_TIMEOUT=90      (seconds; the AI routes stop at 60 s and 15 s)
#
# Macro news quorum (specs/017) — Gemini on Vertex AI. Always passed, with defaults:
#   GOOGLE_GENAI_USE_VERTEXAI=TRUE           (set FALSE to disable the quorum)
#   GOOGLE_CLOUD_PROJECT=$GCP_PROJECT_ID
#   GOOGLE_CLOUD_LOCATION=$CLOUD_RUN_REGION
#   QUORUM_MODEL                             (optional; app default gemini-2.5-flash)
#
# --max-instances stays 1: the daily AI cap is counted in that one instance's memory.
#
# Env vars are applied with --update-env-vars, so values set on the service
# outside this script are kept rather than wiped.

SERVICE="${CLOUD_RUN_SERVICE:-option-sentinel}"
REGION="${CLOUD_RUN_REGION:-us-central1}"
RATE="${RISK_FREE_RATE:-0.045}"
CONCURRENCY="${CLOUD_RUN_CONCURRENCY:-10}"
TIMEOUT="${CLOUD_RUN_TIMEOUT:-90}"
# Prefer the prod redirect URI when deploying; fall back to SCHWAB_REDIRECT_URI
SCHWAB_REDIRECT_URI="${SCHWAB_REDIRECT_URI_PROD:-${SCHWAB_REDIRECT_URI:-}}"
HTTPS_ONLY_VAL="${HTTPS_ONLY:-true}"
DEBUG_VAL="${DEBUG:-false}"
FIREBASE_PROJ="${FIREBASE_PROJECT:-${GCP_PROJECT_ID:-}}"
ALLOWED_ORIGIN_VAL="${ALLOWED_ORIGIN:-https://${FIREBASE_PROJ}.web.app}"

missing=()
for var in GCP_PROJECT_ID SCHWAB_CLIENT_ID SCHWAB_REDIRECT_URI SCHWAB_AUTH_URL SCHWAB_TOKEN_URL; do
  [[ -z "${!var:-}" ]] && missing+=("$var")
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "ERROR: missing required environment variables:"
  for v in "${missing[@]}"; do echo "  $v"; done
  exit 1
fi

if [[ -z "${CLOUD_RUN_SERVICE_ACCOUNT:-}" ]]; then
  echo "ERROR: CLOUD_RUN_SERVICE_ACCOUNT is not set."
  echo "       Run 'bash scripts/setup_gcp_security.sh' once to create the least-privilege"
  echo "       runtime account and the Secret Manager secrets, then add the account to .env."
  exit 1
fi

VERTEX_ENABLED="${GOOGLE_GENAI_USE_VERTEXAI:-TRUE}"
VERTEX_PROJECT="${GOOGLE_CLOUD_PROJECT:-${GCP_PROJECT_ID}}"
VERTEX_LOCATION="${GOOGLE_CLOUD_LOCATION:-${REGION}}"

ENV_VARS="SCHWAB_CLIENT_ID=${SCHWAB_CLIENT_ID},SCHWAB_REDIRECT_URI=${SCHWAB_REDIRECT_URI},SCHWAB_AUTH_URL=${SCHWAB_AUTH_URL},SCHWAB_TOKEN_URL=${SCHWAB_TOKEN_URL},RISK_FREE_RATE=${RATE},HTTPS_ONLY=${HTTPS_ONLY_VAL},DEBUG=${DEBUG_VAL},ALLOWED_ORIGIN=${ALLOWED_ORIGIN_VAL}"
ENV_VARS="${ENV_VARS},GOOGLE_GENAI_USE_VERTEXAI=${VERTEX_ENABLED},GOOGLE_CLOUD_PROJECT=${VERTEX_PROJECT},GOOGLE_CLOUD_LOCATION=${VERTEX_LOCATION}"
for var in QUORUM_MODEL QUORUM_DAILY_CAP; do
  [[ -n "${!var:-}" ]] && ENV_VARS="${ENV_VARS},${var}=${!var}"
done
SECRETS="SCHWAB_CLIENT_SECRET=schwab-client-secret:latest,QUORUM_SEAL_KEY=quorum-seal-key:latest,LOG_PEPPER=log-pepper:latest"
echo "→ Quorum: Vertex AI=${VERTEX_ENABLED}, project=${VERTEX_PROJECT}, location=${VERTEX_LOCATION}"

# Record which commit this revision was built from (used by backend_changed.sh).
# Only uncommitted changes to backend paths mark the build "-dirty".
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mapfile -t BACKEND_PATHS < <(bash "$SCRIPT_DIR/backend_changed.sh" --paths)
COMMIT_SHA="$(git rev-parse --short=12 HEAD 2>/dev/null || echo unknown)"
if [[ -n "$(git status --porcelain -- "${BACKEND_PATHS[@]}" 2>/dev/null)" ]]; then
  COMMIT_SHA="${COMMIT_SHA}-dirty"
fi

echo "→ Deploying $SERVICE to Cloud Run ($REGION) from ${COMMIT_SHA}…"

gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --platform managed \
  --min-instances 0 \
  --max-instances 1 \
  --concurrency "$CONCURRENCY" \
  --timeout "$TIMEOUT" \
  --allow-unauthenticated \
  --service-account "$CLOUD_RUN_SERVICE_ACCOUNT" \
  --project "$GCP_PROJECT_ID" \
  --update-labels "commit-sha=${COMMIT_SHA}" \
  --update-env-vars "${ENV_VARS}" \
  --update-secrets "${SECRETS}"

SERVICE_URL=$(gcloud run services describe "$SERVICE" \
  --region "$REGION" \
  --project "$GCP_PROJECT_ID" \
  --format "value(status.url)")

echo "✓ Backend deployed: $SERVICE_URL"
