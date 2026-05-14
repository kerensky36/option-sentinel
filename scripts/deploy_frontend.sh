#!/usr/bin/env bash
set -euo pipefail

# Deploy the Option Sentinel frontend to Firebase Hosting.
# Usage: bash scripts/deploy_frontend.sh
#
# Required env vars:
#   GCP_PROJECT_ID
#
# Optional env vars:
#   FIREBASE_PROJECT  (defaults to GCP_PROJECT_ID)

FIREBASE_PROJ="${FIREBASE_PROJECT:-${GCP_PROJECT_ID:-}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON="${REPO_ROOT}/.venv/bin/python"
[[ ! -x "$PYTHON" ]] && PYTHON="python3"

if [[ -z "${GCP_PROJECT_ID:-}" ]]; then
  echo "ERROR: missing required environment variable: GCP_PROJECT_ID"
  exit 1
fi

echo "→ Building static frontend…"
"$PYTHON" scripts/build_frontend.py

echo "→ Deploying to Firebase Hosting (project: $FIREBASE_PROJ)…"
firebase deploy --only hosting --project "$FIREBASE_PROJ"

echo "✓ Frontend deployed: https://${FIREBASE_PROJ}.web.app"
