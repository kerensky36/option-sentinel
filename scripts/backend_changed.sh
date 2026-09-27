#!/usr/bin/env bash
set -euo pipefail

# Decide whether the Cloud Run backend needs redeploying.
# Usage: bash scripts/backend_changed.sh <deployed-commit-sha>
#        bash scripts/backend_changed.sh --paths   (print the backend paths)
#
# Exit 0 = backend changed (deploy it), exit 1 = unchanged (skip).
# Compares the deployed commit with the working tree, so committed,
# uncommitted and new untracked files under the backend paths all count.

# Everything that ends up in the Cloud Run image or its deploy config.
# frontend/ is included because the backend also serves the login and
# data-use templates.
BACKEND_PATHS=(src frontend requirements.txt Dockerfile .dockerignore scripts/deploy_backend.sh)

if [[ "${1:-}" == "--paths" ]]; then
  printf '%s\n' "${BACKEND_PATHS[@]}"
  exit 0
fi

deployed="${1:-}"

if [[ -z "$deployed" ]]; then
  echo "no deployed commit recorded"
  exit 0
fi

if [[ "$deployed" == *-dirty ]]; then
  echo "deployed revision was built from uncommitted changes ($deployed)"
  exit 0
fi

if ! git cat-file -e "${deployed}^{commit}" 2>/dev/null; then
  echo "deployed commit $deployed not found locally (try: git fetch)"
  exit 0
fi

existing=()
for p in "${BACKEND_PATHS[@]}"; do
  [[ -e "$p" ]] && existing+=("$p")
done

if ! git diff --quiet "$deployed" -- "${existing[@]}"; then
  echo "backend files changed since $deployed"
  exit 0
fi

if [[ -n "$(git ls-files --others --exclude-standard -- "${existing[@]}")" ]]; then
  echo "new untracked backend files since $deployed"
  exit 0
fi

echo "backend unchanged since $deployed"
exit 1
