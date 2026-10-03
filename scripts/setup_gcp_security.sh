#!/usr/bin/env bash
set -euo pipefail

# One-time GCP hardening for Option Sentinel (specs/022 FR-508). Safe to re-run.
# Usage: bash scripts/setup_gcp_security.sh [--rotate]
#
#   1. Creates the runtime service account option-sentinel-run with only
#      roles/aiplatform.user and roles/logging.logWriter on the project.
#   2. Creates Secret Manager secrets schwab-client-secret, quorum-seal-key and
#      log-pepper, and lets only that account read them. Values are piped on
#      stdin, never passed as arguments. QUORUM_SEAL_KEY and LOG_PEPPER are
#      generated when not set. --rotate adds new versions to existing secrets
#      (e.g. after rotating the Schwab app secret).
#   3. Moves the running Cloud Run service onto the account and the secrets,
#      removing the old plain env vars in the same update.
#   4. Optionally creates a billing budget alert (BILLING_ACCOUNT_ID set).
#
# It never removes roles from other accounts: it prints that step for you.
#
# Required env vars (read from .env): GCP_PROJECT_ID, SCHWAB_CLIENT_SECRET
# Optional: CLOUD_RUN_SERVICE, CLOUD_RUN_REGION, QUORUM_SEAL_KEY, LOG_PEPPER,
#           BILLING_ACCOUNT_ID, MONTHLY_BUDGET_USD (default 50)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
if [[ -f "$REPO_ROOT/.env" && -z "${OPTION_SENTINEL_NO_DOTENV:-}" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
fi

ROTATE=false
[[ "${1:-}" == "--rotate" ]] && ROTATE=true

PROJECT="${GCP_PROJECT_ID:-}"
SERVICE="${CLOUD_RUN_SERVICE:-option-sentinel}"
REGION="${CLOUD_RUN_REGION:-us-central1}"
SA_NAME="option-sentinel-run"
SA="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"

if [[ -z "$PROJECT" || -z "${SCHWAB_CLIENT_SECRET:-}" ]]; then
  echo "ERROR: GCP_PROJECT_ID and SCHWAB_CLIENT_SECRET must be set (in .env or the shell)."
  exit 1
fi

random_value() { python3 -c 'import secrets; print(secrets.token_urlsafe(48))'; }

echo "→ Enabling Secret Manager and Vertex AI APIs…"
gcloud services enable secretmanager.googleapis.com aiplatform.googleapis.com --project="$PROJECT"

echo "→ Runtime service account ${SA}"
if ! gcloud iam service-accounts describe "$SA" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SA_NAME" --project="$PROJECT" \
    --display-name="Option Sentinel Cloud Run runtime"
fi
for role in roles/aiplatform.user roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member="serviceAccount:${SA}" --role="$role" --condition=None >/dev/null
done

put_secret() {  # name value
  local name="$1" value="$2" created=false
  if ! gcloud secrets describe "$name" --project="$PROJECT" >/dev/null 2>&1; then
    gcloud secrets create "$name" --project="$PROJECT" --replication-policy=automatic
    created=true
  fi
  if [[ "$created" == true || "$ROTATE" == true ]]; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --project="$PROJECT" --data-file=-
  fi
  gcloud secrets add-iam-policy-binding "$name" --project="$PROJECT" \
    --member="serviceAccount:${SA}" --role="roles/secretmanager.secretAccessor" >/dev/null
}

echo "→ Secrets (values sent on stdin only)…"
put_secret schwab-client-secret "$SCHWAB_CLIENT_SECRET"
put_secret quorum-seal-key "${QUORUM_SEAL_KEY:-$(random_value)}"
put_secret log-pepper "${LOG_PEPPER:-$(random_value)}"

SECRETS="SCHWAB_CLIENT_SECRET=schwab-client-secret:latest,QUORUM_SEAL_KEY=quorum-seal-key:latest,LOG_PEPPER=log-pepper:latest"
if gcloud run services describe "$SERVICE" --region="$REGION" --project="$PROJECT" >/dev/null 2>&1; then
  echo "→ Moving ${SERVICE} onto ${SA} and Secret Manager…"
  gcloud run services update "$SERVICE" --region="$REGION" --project="$PROJECT" \
    --service-account="$SA" \
    --remove-env-vars=SCHWAB_CLIENT_SECRET,QUORUM_SEAL_KEY,LOG_PEPPER \
    --update-secrets="$SECRETS"
else
  echo "→ ${SERVICE} not deployed yet: deploy_backend.sh will attach the account and secrets."
fi

if [[ -n "${BILLING_ACCOUNT_ID:-}" ]]; then
  echo "→ Billing budget alert (${MONTHLY_BUDGET_USD:-50} USD/month)…"
  gcloud billing budgets create --billing-account="$BILLING_ACCOUNT_ID" \
    --display-name="option-sentinel" \
    --budget-amount="${MONTHLY_BUDGET_USD:-50}USD" \
    --filter-projects="projects/${PROJECT}" \
    --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0 \
    || echo "  (budget not created — it may already exist; check Billing → Budgets & alerts)"
fi

DEFAULT_SA="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)' 2>/dev/null || echo PROJECT_NUMBER)-compute@developer.gserviceaccount.com"
cat <<EOF

✓ Done. Next steps:
  1. Add to .env:   CLOUD_RUN_SERVICE_ACCOUNT=${SA}
     You can now delete SCHWAB_CLIENT_SECRET, QUORUM_SEAL_KEY and LOG_PEPPER from .env
     once you no longer need them locally.
  2. Review the Compute default account (${DEFAULT_SA}) — it no longer needs Vertex AI:
       gcloud projects remove-iam-policy-binding ${PROJECT} \\
         --member=serviceAccount:${DEFAULT_SA} --role=roles/aiplatform.user
  3. See specs/022-ai-cost-guard-hardening/quickstart.md for the budget kill switch,
     Vertex AI quota caps and rotating the Schwab app secret (then re-run with --rotate).
EOF
