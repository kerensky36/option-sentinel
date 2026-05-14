# Deploy Contracts: GCP Cloud Run + Firebase Hosting

**Feature**: 005-cloudrun-firebase-deploy
**Date**: 2026-05-13

---

## Contract 1: Backend Deploy Script (`scripts/deploy_backend.sh`)

### Inputs (environment variables)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GCP_PROJECT_ID` | ✅ | — | GCP project ID |
| `SCHWAB_CLIENT_ID` | ✅ | — | Passed as Cloud Run env var |
| `SCHWAB_CLIENT_SECRET` | ✅ | — | Passed as Cloud Run env var |
| `SCHWAB_REDIRECT_URI` | ✅ | — | Passed as Cloud Run env var |
| `SCHWAB_AUTH_URL` | ✅ | — | Passed as Cloud Run env var |
| `SCHWAB_TOKEN_URL` | ✅ | — | Passed as Cloud Run env var |
| `CLOUD_RUN_SERVICE` | optional | `option-sentinel` | Service name |
| `CLOUD_RUN_REGION` | optional | `us-central1` | Deployment region |
| `RISK_FREE_RATE` | optional | `0.045` | Passed as Cloud Run env var |

### Behaviour

1. Validates all required variables are set; exits non-zero with a clear message if any are missing
2. Runs `gcloud run deploy` with `--source .` (triggers Cloud Build), `--min-instances 0`, `--max-instances 1`, `--allow-unauthenticated`
3. On success: prints the deployed Cloud Run service URL
4. On failure: exits non-zero and surfaces the gcloud error

### Outputs

- Stdout: Cloud Run service URL on success
- Exit code: `0` on success, non-zero on any failure

---

## Contract 2: Frontend Build Script (`scripts/build_frontend.py`)

### Inputs

| Input | Source | Description |
|-------|--------|-------------|
| `frontend/templates/` | Filesystem | Jinja2 templates to pre-render |
| `frontend/static/` | Filesystem | Static assets to copy verbatim |

### Behaviour

1. Creates (or empties) `dist/` directory
2. Copies `frontend/static/` → `dist/static/`
3. Renders `dashboard.html` with `{"current_page": "thesis_monitor"}` → `dist/index.html`
4. Renders `screener.html` with `{"current_page": "covered_call_screener", "setup_required": False}` → `dist/screener/index.html`
5. Prints each output file path on success

### Outputs

- `dist/index.html`
- `dist/screener/index.html`
- `dist/static/**`
- Exit code: `0` on success, non-zero on any failure

---

## Contract 3: Frontend Deploy Script (`scripts/deploy_frontend.sh`)

### Inputs (environment variables)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GCP_PROJECT_ID` | ✅ | — | Firebase project ID (same as GCP project) |
| `CLOUD_RUN_SERVICE_URL` | ✅ | — | Full HTTPS URL of the deployed Cloud Run service |
| `FIREBASE_PROJECT` | optional | `GCP_PROJECT_ID` | Firebase project ID if different |

### Behaviour

1. Validates required variables; exits non-zero if any missing
2. Writes `firebase.json` with the Cloud Run service URL injected as the `serviceId` (or uses a pre-committed `firebase.json` if the service ID matches)
3. Runs `python scripts/build_frontend.py` to produce `dist/`
4. Runs `firebase deploy --only hosting --project $FIREBASE_PROJECT`
5. On success: prints the Firebase Hosting URL

### Outputs

- Stdout: Firebase Hosting URL on success
- Exit code: `0` on success, non-zero on any failure

---

## Contract 4: Combined Deploy Script (`scripts/deploy.sh`)

### Inputs

All variables from Contract 1 and Contract 3.

### Behaviour

1. Runs `deploy_backend.sh` first
2. Captures the Cloud Run service URL from its output
3. Sets `CLOUD_RUN_SERVICE_URL` and runs `deploy_frontend.sh`
4. Prints both URLs on completion
5. If backend deploy fails, does **not** run frontend deploy

### Outputs

- Stdout: Cloud Run URL and Firebase Hosting URL on success
- Exit code: `0` only if both deployments succeed

---

## Contract 5: Firebase Hosting Configuration (`firebase.json`)

```json
{
  "hosting": {
    "public": "dist",
    "cleanUrls": true,
    "trailingSlash": false,
    "headers": [
      {
        "source": "/static/**",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "public, max-age=31536000, immutable"
          }
        ]
      }
    ],
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "option-sentinel",
          "region": "us-central1"
        }
      },
      {
        "source": "/auth/**",
        "run": {
          "serviceId": "option-sentinel",
          "region": "us-central1"
        }
      },
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

**Constraint**: `serviceId` must match the Cloud Run service name. If `CLOUD_RUN_SERVICE` is customised, `firebase.json` must be updated accordingly.

---

## Contract 6: Health Check

The Cloud Run service exposes `GET /health` with no authentication required.

**Response** (200 OK):
```json
{"status": "ok"}
```

This endpoint is used by deploy scripts and Cloud Run's startup probe to verify the service is ready.
