#!/usr/bin/env bash
set -euo pipefail

# Build the self-hosted stylesheet (specs/023 FR-602). Node is build-time only;
# the output is committed so the container and Firebase need no Node.
# CI rebuilds and fails if frontend/static/css/app.css is stale.
cd "$(dirname "${BASH_SOURCE[0]}")/.."
npx --yes tailwindcss@3.4.19 -c tailwind.config.js \
  -i frontend/tailwind.input.css -o frontend/static/css/app.css --minify
