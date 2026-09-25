# Quickstart: Macro News Voting Quorum

## One-time GCP setup

```bash
PROJECT=your-gcp-project
gcloud services enable aiplatform.googleapis.com --project=$PROJECT
SA=$(gcloud run services describe option-sentinel --region=us-central1 \
      --format='value(spec.template.spec.serviceAccountName)')
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:${SA}" --role="roles/aiplatform.user"
gcloud run services update option-sentinel --region=us-central1 \
  --update-env-vars=GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=$PROJECT,GOOGLE_CLOUD_LOCATION=us-central1
```

Local dev: `gcloud auth application-default login` and set the same three variables in `.env`. Optionally `QUORUM_MODEL=<gemini model id>`.

## Automated checks

```bash
pytest tests/unit/test_quorum_tally.py tests/unit/test_news_feeds.py \
       tests/unit/test_quorum_agents.py tests/contract/test_quorum_api.py -q
```

## Browser verification

1. **Button present** — Dashboard shows a 🗳 Quorum button on every standalone option row and every spread summary row (FR-001).
2. **No payoff side-effect** — Clicking Quorum does not open/close the payoff graph for that row.
3. **Loading → result** — Panel appears under the row with a spinner, then verdict + tally within 60 s (SC-001).
4. **Majority** — Verdict badge equals the action with ≥ 3 votes; otherwise "NO CONSENSUS — status quo: hold".
5. **Analyst cards** — Five cards with lens, vote, confidence %, rationale; ROLL shows direction; failed seats show "abstained".
6. **Headlines** — Each shows publisher + title, opens in a new tab.
7. **Spread** — Quorum on a spread summary row evaluates all legs together (network tab: request body lists every leg symbol).
8. **Toggle** — Clicking the same Quorum button closes the panel; clicking another row's button moves it.
9. **Not configured** — Unset `GOOGLE_CLOUD_PROJECT`, click Quorum → "Quorum is not configured on this server".
10. **Demo mode** — Demo login, click Quorum → canned result, no request to `/api/quorum/vote`.
11. **Mobile** — At 375 px width analyst cards stack in one column, no horizontal page scroll inside the panel.
12. **Privacy** — Close the panel, inspect sessionStorage: no quorum data stored (FR-015).
