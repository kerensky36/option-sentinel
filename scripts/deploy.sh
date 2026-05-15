#!/usr/bin/env bash
set -euo pipefail

# Deploy Option Sentinel: backend to Cloud Run, then frontend to Firebase Hosting.
# Usage: bash scripts/deploy.sh
#
# Required env vars: see deploy_backend.sh and deploy_frontend.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE="${CLOUD_RUN_SERVICE:-option-sentinel}"
REGION="${CLOUD_RUN_REGION:-us-central1}"
FIREBASE_PROJ="${FIREBASE_PROJECT:-${GCP_PROJECT_ID:-}}"

echo "=== Option Sentinel Deploy ==="
echo ""

echo "→ Deploying backend to Cloud Run…"
bash "$SCRIPT_DIR/deploy_backend.sh"

SERVICE_URL=$(gcloud run services describe "$SERVICE" \
  --region "$REGION" \
  --project "$GCP_PROJECT_ID" \
  --format "value(status.url)" 2>/dev/null)

echo ""
echo "→ Deploying frontend to Firebase Hosting…"
bash "$SCRIPT_DIR/deploy_frontend.sh"

echo ""
echo "=== Deploy complete ==="
echo "  Backend:  $SERVICE_URL"
echo "  Frontend: https://${FIREBASE_PROJ}.web.app"
echo ""
echo "⚠  Remember to update SCHWAB_REDIRECT_URI to:"
echo "   https://${FIREBASE_PROJ}.web.app/auth/callback"
echo "   and register it in your Schwab developer app."
