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

SERVICE="${CLOUD_RUN_SERVICE:-option-sentinel}"
REGION="${CLOUD_RUN_REGION:-us-central1}"
RATE="${RISK_FREE_RATE:-0.045}"
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

echo "→ Deploying $SERVICE to Cloud Run ($REGION)…"

gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --platform managed \
  --min-instances 0 \
  --max-instances 1 \
  --allow-unauthenticated \
  --project "$GCP_PROJECT_ID" \
  --set-env-vars "SCHWAB_CLIENT_ID=${SCHWAB_CLIENT_ID},SCHWAB_CLIENT_SECRET=${SCHWAB_CLIENT_SECRET},SCHWAB_REDIRECT_URI=${SCHWAB_REDIRECT_URI},SCHWAB_AUTH_URL=${SCHWAB_AUTH_URL},SCHWAB_TOKEN_URL=${SCHWAB_TOKEN_URL},RISK_FREE_RATE=${RATE},HTTPS_ONLY=${HTTPS_ONLY_VAL},DEBUG=${DEBUG_VAL},ALLOWED_ORIGIN=${ALLOWED_ORIGIN_VAL}"

SERVICE_URL=$(gcloud run services describe "$SERVICE" \
  --region "$REGION" \
  --project "$GCP_PROJECT_ID" \
  --format "value(status.url)")

echo "✓ Backend deployed: $SERVICE_URL"
