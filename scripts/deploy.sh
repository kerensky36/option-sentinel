#!/usr/bin/env bash
set -euo pipefail

# Deploy Option Sentinel: backend to Cloud Run (only if it changed), then
# frontend to Firebase Hosting.
# Usage: bash scripts/deploy.sh [--force-backend | --skip-backend]
#
# The backend is redeployed only when src/, frontend/, requirements.txt,
# Dockerfile, .dockerignore or deploy_backend.sh differ from the commit the
# live Cloud Run service was built from (its "commit-sha" label).
# Reads credentials and config from .env in the repo root — no manual env var export needed.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Load .env if present (won't override vars already set in the shell)
if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
fi

SERVICE="${CLOUD_RUN_SERVICE:-option-sentinel}"
REGION="${CLOUD_RUN_REGION:-us-central1}"
FIREBASE_PROJ="${FIREBASE_PROJECT:-${GCP_PROJECT_ID:-}}"

BACKEND_MODE="auto"
for arg in "$@"; do
  case "$arg" in
    --force-backend) BACKEND_MODE="force" ;;
    --skip-backend)  BACKEND_MODE="skip" ;;
    *) echo "Unknown option: $arg (use --force-backend or --skip-backend)"; exit 1 ;;
  esac
done

if [[ -z "${GCP_PROJECT_ID:-}" ]]; then
  echo "ERROR: missing required environment variable: GCP_PROJECT_ID"
  exit 1
fi

echo "=== Option Sentinel Deploy ==="
echo ""

cd "$REPO_ROOT"
DEPLOYED_SHA=$(gcloud run services describe "$SERVICE" \
  --region "$REGION" \
  --project "$GCP_PROJECT_ID" \
  --format "value(metadata.labels.commit-sha)" 2>/dev/null || true)

if [[ "$BACKEND_MODE" == "skip" ]]; then
  echo "→ Backend: skipped (--skip-backend)"
elif [[ "$BACKEND_MODE" == "force" ]]; then
  echo "→ Backend: forced (--force-backend)"
  bash "$SCRIPT_DIR/deploy_backend.sh"
elif reason=$(bash "$SCRIPT_DIR/backend_changed.sh" "$DEPLOYED_SHA"); then
  echo "→ Backend: deploying — ${reason}"
  bash "$SCRIPT_DIR/deploy_backend.sh"
else
  echo "→ Backend: ${reason} — skipping Cloud Run deploy"
fi

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
echo "⚠  Ensure https://${FIREBASE_PROJ}.web.app/auth/callback is registered"
echo "   as an allowed callback URL in your Schwab developer app."
