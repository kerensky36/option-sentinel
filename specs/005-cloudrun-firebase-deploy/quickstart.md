# Quickstart: GCP Cloud Run + Firebase Hosting Deployment

**Feature**: 005-cloudrun-firebase-deploy
**Date**: 2026-05-13

---

## Prerequisites

- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- [Firebase CLI](https://firebase.google.com/docs/cli) installed (`npm install -g firebase-tools`)
- A GCP project with billing enabled
- Cloud Run API and Firebase Hosting enabled on the project
- A Schwab developer app with a callback URL that matches your Firebase Hosting domain

---

## One-time Setup

### 1. Authenticate

```bash
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID
firebase login
```

### 2. Enable required APIs

```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firebase.googleapis.com
```

### 3. Configure Firebase project

```bash
firebase use --add
# Select your GCP project ID when prompted
# This writes .firebaserc
```

### 4. Set environment variables

Copy `.env.example` to `.env` and fill in your Schwab credentials. Then export deploy-time variables:

```bash
export GCP_PROJECT_ID=your-project-id
export SCHWAB_CLIENT_ID=your_app_key
export SCHWAB_CLIENT_SECRET=your_app_secret
export SCHWAB_REDIRECT_URI=https://YOUR-PROJECT.web.app/auth/callback
export SCHWAB_AUTH_URL=https://api.schwabapi.com/v1/oauth/authorize
export SCHWAB_TOKEN_URL=https://api.schwabapi.com/v1/oauth/token
```

> **Important**: `SCHWAB_REDIRECT_URI` must be set to your Firebase Hosting URL + `/auth/callback`. Update this value in both your Schwab developer app's allowed redirect URIs and your local environment.

---

## Deployment

### Full deploy (backend + frontend)

```bash
bash scripts/deploy.sh
```

Output on success:
```
✓ Backend deployed: https://option-sentinel-xxxxxxxx-uc.a.run.app
✓ Frontend deployed: https://your-project.web.app
```

### Backend only

```bash
bash scripts/deploy_backend.sh
```

### Frontend only (requires backend already deployed)

```bash
export CLOUD_RUN_SERVICE_URL=https://option-sentinel-xxxxxxxx-uc.a.run.app
bash scripts/deploy_frontend.sh
```

---

## Post-Deploy Verification

1. Open `https://YOUR-PROJECT.web.app`
2. You should see the login page — click "Connect Schwab Account"
3. Complete the Schwab OAuth flow
4. The dashboard loads and the Refresh button fetches live positions

### Smoke checks

```bash
# Backend health
curl https://option-sentinel-xxxxxxxx-uc.a.run.app/health
# → {"status":"ok"}

# Frontend SPA routing (should not 404)
curl -I https://YOUR-PROJECT.web.app/screener
# → HTTP/2 200
```

---

## Cold Start

Cloud Run is configured with `min-instances=0` (scale to zero). The first request after an idle period will take up to 3 seconds. Subsequent requests are fast.

The dashboard and screener pages are served as static HTML from Firebase CDN — they load instantly even when Cloud Run is cold. Only the Refresh API call waits for Cloud Run.

---

## Re-deploying

After code changes, run the full deploy again:

```bash
bash scripts/deploy.sh
```

`dist/` is regenerated on every frontend deploy. The backend container is rebuilt by Cloud Build on every backend deploy.

---

## OAuth Callback Domain Change

If your Firebase Hosting URL changes (e.g., new project, custom domain), you must:

1. Update `SCHWAB_REDIRECT_URI` in your environment and in the `deploy_backend.sh` invocation
2. Update the allowed redirect URI in your Schwab developer app at developer.schwab.com
3. Redeploy the backend with the new `SCHWAB_REDIRECT_URI`
4. Redeploy the frontend (no code changes needed)

---

## Tear Down

```bash
# Delete Cloud Run service
gcloud run services delete option-sentinel --region us-central1

# Delete Firebase Hosting site
firebase hosting:disable
```
