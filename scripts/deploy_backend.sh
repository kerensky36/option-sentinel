#!/usr/bin/env bash
set -euo pipefail

# Deploy the Option Sentinel backend to GCP Cloud Run.
# Usage: bash scripts/deploy_backend.sh
#
# Required env vars:
#   GCP_PROJECT_ID, SCHWAB_CLIENT_ID, SCHWAB_CLIENT_SECRET,
#   SCHWAB_REDIRECT_URI, SCHWAB_AUTH_URL, SCHWAB_TOKEN_URL
#
# Optional env vars (defaults shown):
#   CLOUD_RUN_SERVICE=option-sentinel
#   CLOUD_RUN_REGION=us-central1
#   RISK_FREE_RATE=0.045
#   HTTPS_ONLY=true     (set HSTS header; default true in prod)
#   DEBUG=false         (suppress stack traces; default false in prod)
#   ALLOWED_ORIGIN      (CORS allowed origin; defaults to Firebase hosting URL)
#   LOG_PEPPER          (HMAC pepper for IP hashing in audit log)
#
# Macro news quorum (specs/017) — passed through only when set; without
# GOOGLE_GENAI_USE_VERTEXAI + GOOGLE_CLOUD_PROJECT the Quorum button shows
# "not configured" (unless they were already set on the service):
#   GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, QUORUM_MODEL
#
# Env vars are applied with --update-env-vars, so values set on the service
# outside this script are kept rather than wiped.

SERVICE="${CLOUD_RUN_SERVICE:-option-sentinel}"
REGION="${CLOUD_RUN_REGION:-us-central1}"
RATE="${RISK_FREE_RATE:-0.045}"
# Prefer the prod redirect URI when deploying; fall back to SCHWAB_REDIRECT_URI
SCHWAB_REDIRECT_URI="${SCHWAB_REDIRECT_URI_PROD:-${SCHWAB_REDIRECT_URI:-}}"
HTTPS_ONLY_VAL="${HTTPS_ONLY:-true}"
DEBUG_VAL="${DEBUG:-false}"
FIREBASE_PROJ="${FIREBASE_PROJECT:-${GCP_PROJECT_ID:-}}"
ALLOWED_ORIGIN_VAL="${ALLOWED_ORIGIN:-https://${FIREBASE_PROJ}.web.app}"

missing=()
for var in GCP_PROJECT_ID SCHWAB_CLIENT_ID SCHWAB_CLIENT_SECRET SCHWAB_REDIRECT_URI SCHWAB_AUTH_URL SCHWAB_TOKEN_URL; do
  [[ -z "${!var:-}" ]] && missing+=("$var")
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "ERROR: missing required environment variables:"
  for v in "${missing[@]}"; do echo "  $v"; done
  exit 1
fi

ENV_VARS="SCHWAB_CLIENT_ID=${SCHWAB_CLIENT_ID},SCHWAB_CLIENT_SECRET=${SCHWAB_CLIENT_SECRET},SCHWAB_REDIRECT_URI=${SCHWAB_REDIRECT_URI},SCHWAB_AUTH_URL=${SCHWAB_AUTH_URL},SCHWAB_TOKEN_URL=${SCHWAB_TOKEN_URL},RISK_FREE_RATE=${RATE},HTTPS_ONLY=${HTTPS_ONLY_VAL},DEBUG=${DEBUG_VAL},ALLOWED_ORIGIN=${ALLOWED_ORIGIN_VAL}"
for var in LOG_PEPPER GOOGLE_GENAI_USE_VERTEXAI GOOGLE_CLOUD_PROJECT GOOGLE_CLOUD_LOCATION QUORUM_MODEL; do
  [[ -n "${!var:-}" ]] && ENV_VARS="${ENV_VARS},${var}=${!var}"
done
if [[ -z "${GOOGLE_CLOUD_PROJECT:-}" ]]; then
  echo "note: GOOGLE_CLOUD_PROJECT not set in .env — Quorum relies on the value already on the service."
fi

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
  --allow-unauthenticated \
  --project "$GCP_PROJECT_ID" \
  --update-labels "commit-sha=${COMMIT_SHA}" \
  --update-env-vars "${ENV_VARS}"

SERVICE_URL=$(gcloud run services describe "$SERVICE" \
  --region "$REGION" \
  --project "$GCP_PROJECT_ID" \
  --format "value(status.url)")

echo "✓ Backend deployed: $SERVICE_URL"
