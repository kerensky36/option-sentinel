# Research: Macro News Voting Quorum

## D-001 — Agent framework: Google ADK 2.10.0 (`google-adk==2.10.0`)

**Decision**: Build every agent as an ADK `LlmAgent` executed by an ADK `Runner` with an `InMemorySessionService`.
**Rationale**: Requested by the user; ADK is Google's first-party agent framework and talks to Vertex AI Gemini natively via `google-genai`. `InMemorySessionService` created inside the request and dropped on return keeps the server stateless (Constitution I, II "Zero shared server state").
**Alternatives**: Raw `google-genai` calls (less structure, no agent abstraction); LangGraph (not Google-native, not requested).

## D-002 — Fan-out: one Runner per seat + `asyncio.gather`, not `ParallelAgent`

**Decision**: Run the five analyst seats as five independent `LlmAgent`s, each in its own `Runner`, concurrently via `asyncio.gather`, each wrapped in `asyncio.wait_for`. Any exception, timeout, or schema-validation failure in one seat becomes an abstention for that seat only.
**Rationale**: Prototyped against ADK 2.10.0 with a fake model: inside a `ParallelAgent`, one seat returning non-JSON raises `pydantic.ValidationError` out of `Runner.run_async` and aborts the whole run — incompatible with FR-005 ("an abstention MUST NOT prevent the other seats from voting"). In addition, ADK 2.x emits `DeprecationWarning: ParallelAgent is deprecated in favor of Workflow`. `Workflow` is new, graph-based, and its error semantics also shut the whole graph down on a node error. Per-seat runners give exact isolation with plain asyncio.
**Alternatives**: `ParallelAgent` (rejected: all-or-nothing failure, deprecated); `Workflow` (rejected: same failure coupling, API still settling).

## D-003 — Model provider: Vertex AI via environment configuration

**Decision**: `google-genai` reads `GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`; credentials come from Application Default Credentials (the Cloud Run service account, which needs `roles/aiplatform.user`). Model name from `QUORUM_MODEL` (default `gemini-2.5-flash`). The endpoint returns 503 unless `GOOGLE_GENAI_USE_VERTEXAI` is truthy and `GOOGLE_CLOUD_PROJECT` is set (FR-014).
**Rationale**: User choice. No API key to store or leak; data governed by the operator's own GCP project.

## D-004 — News: public RSS feeds + one search-grounded research agent

**Decision**:
1. Deterministic headlines from public RSS feeds, fetched with the existing `httpx` dependency (5 s timeout each, concurrently) and parsed with `feedparser==6.0.14`:
   - CNBC Top News `https://www.cnbc.com/id/100003114/device/rss/rss.html`
   - CNBC Economy `https://www.cnbc.com/id/20910258/device/rss/rss.html`
   - Yahoo Finance `https://finance.yahoo.com/news/rssindex`
   - Bloomberg Markets `https://feeds.bloomberg.com/markets/news.rss`
   - Yahoo Finance per-ticker `https://feeds.finance.yahoo.com/rss/2.0/headline?s={UNDERLYING}&region=US&lang=en-US`
2. A `MacroResearcher` `LlmAgent` with ADK's built-in `google_search` tool, instructed to prefer cnbc.com, finance.yahoo.com, and bloomberg.com, writes a ≤ 1200-char macro brief shared with every seat (FR-010).
**Rationale**: The user asked for financial news sources (CNBC, Yahoo Finance, Bloomberg). RSS is keyless, citable (title + link shown in UI, FR-016) and testable offline. Bloomberg's public feed is sparse and articles are paywalled, so search grounding fills the gap. `google_search` must sit alone on its agent (ADK built-in tool limitation), hence a dedicated researcher.
**Alternatives**: Scraping article pages (ToS/paywall issues, brittle); FRED statistics API (user explicitly chose news sources).
**Why feedparser**: Handles RSS 0.9x/1.0/2.0/Atom, malformed feeds, and date normalisation; hand-rolling this on `xml.etree` is more code and more risk. Pure-Python, no transitive deps.

## D-005 — Tally is deterministic Python, not an agent

**Decision**: `tally_votes()` is a pure function: quorum ≥ 3 valid of 5 seats; verdict = action with ≥ 3 votes; else `NO_CONSENSUS`; below quorum `NO_QUORUM` (FR-007). Exhaustively tested over all 4⁵ = 1024 seat outcomes (SC-002).
**Rationale**: A model-based "chair" could be swayed by prompt injection in headlines; the vote count must be auditable arithmetic.

## D-006 — Prompt-injection containment

**Decision**: (a) Seat instructions are static and contain no untrusted text; all data (position + headlines + brief) goes in the user message as a JSON document explicitly labelled as untrusted data. (b) Seats have **no tools**, so injected text cannot cause side effects. (c) Output is constrained by `output_schema` (enum action, bounded confidence) — anything else is an abstention. (d) Server never acts on votes. (e) Frontend escapes every string and only emits `http(s)` links with `rel="noopener noreferrer"`.

## D-007 — Server re-fetches the position; client sends symbols only

**Decision**: `POST /api/quorum/vote {symbols, account_hash}`. The route calls the existing `fetch_positions_and_greeks()` with the caller's token, which already validates `account_hash` against the token (IDOR guard), then selects the requested legs.
**Rationale**: Prevents clients from feeding fabricated positions/prompts to the model on the operator's bill; reuses existing validated code path (FR-002, FR-003).

## D-008 — Constitution v3.3.0 (approved by project owner 2026-09-25)

**Decision**: Principle I now allows position and market data to be sent to Vertex AI and forbids user-identifiable or pedigree data. It also requires an in-app Data Use Disclosure listing every use of user data.
**Implementation consequences**: (a) `PositionLegContext` is an allow-list of fields — nothing else can reach the prompt. (b) A test captures every fake-model request and asserts the account hash, token, and OCC symbol-to-account linkage never appear. (c) New `/data-use` page, linked from login and nav (FR-019), and a one-line notice + link in the quorum panel (FR-020).
