# AI-News-Monitor Next Version Prompt: Intelligent Source Discovery, Multi-Source Verification, Social Media Ingestion, and DeepSeek Provider

You are continuing development of the existing AI-News-Monitor project.

Before coding, read the existing project context and docs if present:

- `CHATBOT_CONTEXT.md`
- `HANDOFF.md`
- `README.md`
- `SOURCE_GUIDE.md`
- `NOTIFICATION_GUIDE.md`
- `config.example.yaml`
- existing tests
- existing source ingestion / notification / LLM provider modules

## Core Goal

Upgrade AI-News-Monitor from a user-specified-source monitor into an intelligent topic-based monitoring system.

The system should still support user-provided websites/RSS/API sources, but it should also be able to:

1. Accept a user-defined topic, theme, or prompt.
2. Decide which data sources are suitable for that topic.
3. Fetch from those sources.
4. Evaluate source credibility and factual reliability before notifying the user.
5. Merge reports from different sources about the same event/topic.
6. Produce a stronger final LLM report with links, timeline, confidence, and source comparison.
7. Add DeepSeek API as a reliable alternative LLM provider.
8. Extend source types beyond tech/finance to politics, history, science, culture, global events, etc.
9. Add social media ingestion, especially X.com, as an optional source type.

The project should remain clean, modular, GitHub-ready, bilingual-friendly, and easy to configure.

---

## Non-Negotiable Principles

Do not break existing basic functionality.

Keep the existing user-defined website / RSS / manual source behavior working.

Do not hardcode API keys, passwords, user prompts, destination accounts, or private credentials.

Do not put Chinese text inside code identifiers, internal constants, or implementation comments unless localization files are explicitly intended for user-facing text.

Use configuration files and environment variables.

Respect source terms, robots.txt, API rate limits, and paywalls.

Do not implement unsafe scraping behind login walls or bypass protections.

Social media content must be treated as lower-confidence evidence unless corroborated by other reliable sources.

Politics-related topics must be handled neutrally. Do not optimize for persuasion. The goal is factual monitoring, source comparison, and transparent uncertainty.

---

## Feature 1: Intelligent Source Discovery and Source Selection

Currently the user can provide sources manually. Add a new source discovery layer.

### Required Behavior

When the user creates or edits a topic, the system should support three modes:

```yaml
source_mode: manual
```

```yaml
source_mode: auto
```

```yaml
source_mode: hybrid
```

Meaning:

- `manual`: only use user-provided sources.
- `auto`: system chooses sources based on topic.
- `hybrid`: use user-provided sources first, then add high-quality discovered sources.

### Source Discovery Logic

Implement a module like:

```txt
src/sources/source_discovery.py
src/sources/source_registry.py
src/sources/source_ranker.py
```

The system should classify the topic domain first:

- technology
- AI industry
- finance
- public companies
- politics
- elections
- geopolitics
- history
- science
- health
- culture
- general breaking news
- user-defined custom domain

Then it should select source categories appropriate to that domain.

Examples:

### Tech / AI

Prefer:

- official company blogs
- GitHub releases
- arXiv / papers
- SEC filings if public company related
- reputable tech media
- official API docs
- RSS feeds
- selected X accounts only if configured

### Finance / Stocks

Prefer:

- exchange announcements
- company investor relations
- SEC / EDGAR
- official earnings reports
- reputable financial media
- market data providers if configured

### Politics / Geopolitics

Prefer:

- official government pages
- official press releases
- parliamentary / congressional records
- election commission sites
- reputable news agencies
- multiple ideologically different sources
- fact-checking organizations
- selected social media accounts only as early-signal sources, not final evidence

### History

Prefer:

- encyclopedic / academic sources
- university sources
- archives
- museum sources
- primary documents if available
- stable references rather than breaking-news feeds

### Science

Prefer:

- journals
- preprint servers
- university press releases
- research institution pages
- reputable science reporting

### Implementation Requirements

Create a `SourceCandidate` data model with fields similar to:

```python
class SourceCandidate:
    id: str
    name: str
    url: str
    source_type: str  # rss, website, api, x, github, arxiv, sec, gov, academic, etc.
    domain_tags: list[str]
    country_or_region: str | None
    language: str | None
    credibility_hint: float | None
    cost_hint: str | None  # free, paid, unknown
    requires_api_key: bool
    enabled_by_default: bool
    notes: str | None
```

Create a `SelectedSource` model with:

```python
class SelectedSource:
    candidate: SourceCandidate
    reason: str
    expected_value: str
    risk: str | None
    priority: int
```

The user should be able to see why a source was chosen.

---

## Feature 2: Source Credibility and Reality Evaluation

Add a source credibility and claim verification layer.

The system should not blindly notify the user just because one source says something.

### Required Behavior

Before sending notifications, run the collected items through a verification pipeline.

Create something like:

```txt
src/verification/credibility.py
src/verification/claim_extraction.py
src/verification/corroboration.py
src/verification/report_quality.py
```

### Source Credibility Score

Each source should receive a score based on:

- source type
- official vs unofficial
- historical reliability if stored
- domain reputation if configured
- whether the content includes primary evidence
- whether the source is social media
- whether other independent sources confirm the same claim
- whether the source has obvious clickbait or low-content structure
- whether the source is an anonymous post
- whether the source is reposting another source

Use a transparent scoring model. It does not need to be perfect, but it must be explainable.

Example output:

```json
{
  "source_name": "Example News",
  "credibility_score": 0.78,
  "confidence_level": "medium",
  "reasons": [
    "Known news outlet",
    "Specific named source included",
    "Partially corroborated by 2 other sources"
  ],
  "risks": [
    "No primary document linked"
  ]
}
```

### Claim-Level Corroboration

Extract key claims from each article/post.

Example:

```json
{
  "claim": "Company X announced a new AI accelerator.",
  "claim_type": "announcement",
  "entities": ["Company X"],
  "time": "2026-05-26",
  "supporting_sources": ["official blog", "reputable media"],
  "contradicting_sources": [],
  "confidence": 0.86
}
```

### Notification Gate

Before notifying the user, decide whether the item is:

- verified enough
- interesting but unconfirmed
- low-confidence rumor
- duplicate
- not relevant

Only send high-confidence or clearly labelled developing reports.

If social media is the only source, label the report clearly:

```txt
Status: Unconfirmed social-media signal
Do not treat this as verified until confirmed by primary or reputable secondary sources.
```

---

## Feature 3: Multi-Source Event Clustering and Better Final Reports

If different sources report the same topic/event, the system should not send separate noisy notifications.

Instead, cluster related items and produce one better report.

### Required Behavior

Add an event clustering layer:

```txt
src/aggregation/event_clusterer.py
src/aggregation/topic_timeline.py
src/aggregation/deduplication.py
```

Cluster based on:

- named entities
- event type
- semantic similarity
- URLs
- timestamps
- source references
- title similarity
- extracted claims

### Final Report Structure

The LLM should produce a clean report like:

```md
# Event Summary

## What happened

Clear 3-6 sentence explanation.

## Why it matters

Explain relevance to the user's topic.

## Timeline

- 2026-05-26 09:20: First signal appeared on X from ...
- 2026-05-26 10:05: Official statement published by ...
- 2026-05-26 11:30: Reputable media confirmed ...

## Source Comparison

| Source | Type | Main Claim | Confidence | Notes |
|---|---|---|---|---|

## Verification Status

High / Medium / Low confidence.

Explain why.

## Links

- Source 1
- Source 2
- Source 3

## Suggested User Action

Only if useful. Keep it concise.
```

For breaking news, include uncertainty.

For historical topics, include source stability and whether the information is primary, secondary, or interpretive.

For finance topics, do not make investment promises. Avoid saying something "will rise" or "will hit limit-up." Provide risk-aware summaries only.

---

## Feature 4: Social Media Source Support, Especially X.com

Add social media as an optional source type.

Start with X.com.

### Important Constraints

X.com should be implemented through official API support where possible.

Do not scrape private, login-protected, or restricted pages.

X recent search only covers recent posts, so design it as a near-real-time signal source, not a full archive.

X API can be paid. Add config warnings and cost controls.

### Required Config

Add to `config.example.yaml`:

```yaml
social_sources:
  x:
    enabled: false
    bearer_token_env: X_BEARER_TOKEN
    max_posts_per_topic_per_run: 25
    include_retweets: false
    min_author_followers: null
    trusted_accounts: []
    blocked_accounts: []
    search_recent_days_limit: 7
    cost_guard:
      enabled: true
      daily_max_read_posts: 500
      warn_when_reaching_percent: 80
```

### Required Code

Implement:

```txt
src/sources/social/x_client.py
src/sources/social/x_query_builder.py
src/sources/social/x_normalizer.py
```

Normalized social item:

```python
class SocialPostItem:
    platform: str
    post_id: str
    url: str
    author_id: str | None
    author_username: str | None
    text: str
    created_at: datetime
    metrics: dict
    referenced_urls: list[str]
    source_confidence_hint: float
```

### X Query Builder

Given a topic, generate X search queries carefully.

Examples:

- include keywords
- include entity names
- exclude spammy terms
- optionally filter language
- optionally use trusted accounts

Do not over-query.

Do not query X by default unless the user enables it or source_mode is auto/hybrid and config allows social sources.

---

## Feature 5: DeepSeek API Provider

Add DeepSeek as another LLM provider choice.

The current system likely already supports one or more LLM APIs. Extend the provider abstraction rather than hardcoding DeepSeek.

### Required Config

Add to `config.example.yaml`:

```yaml
llm:
  provider: openai
  fallback_providers: []

  providers:
    openai:
      enabled: true
      api_key_env: OPENAI_API_KEY
      model: gpt-4.1-mini

    deepseek:
      enabled: false
      api_key_env: DEEPSEEK_API_KEY
      base_url: https://api.deepseek.com
      model: deepseek-v4-flash
      timeout_seconds: 60
      max_retries: 3
      retry_backoff_seconds: 2
      thinking:
        enabled: false
        reasoning_effort: medium
```

### Required Behavior

Implement or update:

```txt
src/llm/provider_base.py
src/llm/openai_provider.py
src/llm/deepseek_provider.py
src/llm/router.py
```

The provider router should support:

- primary provider
- fallback provider
- timeout
- retry with exponential backoff
- structured JSON output where possible
- clear error messages
- safe degradation if one provider fails

DeepSeek should use OpenAI-compatible SDK or HTTP interface.

Do not use deprecated model names as the default.

Use `deepseek-v4-flash` as the default cost-effective model unless the config says otherwise.

Support `deepseek-v4-pro` as an option.

### Reliability Requirements

Add:

- health check command
- provider smoke test
- structured output parsing test
- retry test
- fallback test

Example CLI or script behavior:

```bash
python -m ai_news_monitor doctor --check-llm
python -m ai_news_monitor doctor --check-sources
```

---

## Feature 6: Topic Generalization

The system must not assume every topic is tech or finance.

Update prompt templates, source selection, UI labels, and docs so topics can include:

- AI industry
- semiconductor
- finance
- politics
- elections
- geopolitics
- history
- science
- culture
- public policy
- local news
- user-defined custom areas

### Required Topic Schema

Create or update topic config like:

```yaml
topics:
  - id: ai_infrastructure
    name: AI Infrastructure
    user_prompt: "Track important updates about AI chips, data centers, memory, networking, and power infrastructure."
    language: en
    source_mode: hybrid
    domains:
      - technology
      - finance
    preferred_regions:
      - US
      - China
      - Taiwan
      - EU
    social_enabled: false
    notification_threshold:
      min_relevance_score: 0.72
      min_confidence_score: 0.65
    report_style:
      include_timeline: true
      include_source_comparison: true
      include_user_action: true
```

Add another example:

```yaml
  - id: geopolitics_example
    name: Geopolitics Example
    user_prompt: "Track major developments in US-China technology policy and export controls."
    language: en
    source_mode: hybrid
    domains:
      - politics
      - technology
      - public_policy
    social_enabled: true
    notification_threshold:
      min_relevance_score: 0.75
      min_confidence_score: 0.70
```

---

## Feature 7: UI / Browser Output Improvements

The browser-side output should remain highly concise and readable.

Avoid code overflow and raw JSON leakage in the UI.

For each report card, show:

- title
- status badge: verified / developing / unconfirmed / low-confidence
- relevance score
- confidence score
- short summary
- timeline toggle
- source comparison toggle
- links
- notification status

Do not show huge raw LLM output unless user expands debug mode.

Add debug mode separately:

```yaml
ui:
  debug_mode: false
```

When `debug_mode` is false, hide:

- raw JSON
- raw prompts
- stack traces
- long source payloads
- internal scoring details

When errors happen, show clean user-facing messages and write technical details to logs.

---

## Feature 8: Tests

Add or update tests.

Required tests:

```txt
tests/test_source_discovery.py
tests/test_source_ranking.py
tests/test_claim_corroboration.py
tests/test_event_clustering.py
tests/test_report_generation.py
tests/test_deepseek_provider.py
tests/test_x_source_config.py
tests/test_notification_gate.py
tests/test_ui_report_sanitization.py
```

Test cases should cover:

1. Manual source mode still works.
2. Auto source mode selects reasonable sources for tech.
3. Auto source mode selects reasonable sources for politics.
4. History topic does not use breaking-news-only sources.
5. X.com is disabled by default.
6. X.com requires a bearer token when enabled.
7. Social-only reports are labelled unconfirmed.
8. Multiple sources about same event are clustered.
9. Contradictory claims are surfaced, not hidden.
10. DeepSeek provider can be configured without breaking OpenAI provider.
11. LLM fallback works if DeepSeek fails.
12. UI does not leak raw JSON/code by default.

Use mocked API responses. Do not require real paid API keys in CI.

---

## Feature 9: Documentation

Update docs:

- `README.md`
- `SOURCE_GUIDE.md`
- `NOTIFICATION_GUIDE.md`
- `docs/LLM_PROVIDERS.md`
- `docs/SOCIAL_SOURCES.md`
- `docs/VERIFICATION_PIPELINE.md`
- `docs/RELEASE_CHECKLIST.md`

Docs must explain:

- manual / auto / hybrid source modes
- how source discovery works
- how credibility score works
- how social media is handled
- why X.com may cost money
- how to set `X_BEARER_TOKEN`
- how to set `DEEPSEEK_API_KEY`
- how to choose OpenAI vs DeepSeek
- how fallback providers work
- how to avoid over-notification
- how to interpret low-confidence reports

Add Chinese and English user-facing explanations where the project already supports bilingual docs.

Implementation code should remain English-only.

---

## Feature 10: Migration and Compatibility

Do not force existing users to rewrite their config.

If old config format exists, migrate safely.

Add default values so old configs still run.

If a field is missing, assume:

```yaml
source_mode: manual
social_enabled: false
```

Add config validation with helpful error messages.

---

## Expected Final State

At the end, the project should be able to:

1. Run existing manual RSS / website monitoring.
2. Accept a broad user topic.
3. Select good sources automatically.
4. Optionally use X.com as a social media signal source.
5. Score credibility and confidence.
6. Cluster multiple reports about the same event.
7. Generate one clean, useful report instead of noisy repeated notifications.
8. Show a clear timeline for a specific event.
9. Use OpenAI or DeepSeek as the LLM provider.
10. Fall back reliably if one LLM provider fails.
11. Notify the user only after relevance and confidence checks.
12. Keep browser UI clean and concise.
13. Pass all tests.

---

## Suggested Work Order

1. Inspect current architecture.
2. Identify existing source ingestion, LLM, notification, and UI modules.
3. Add or refactor provider abstraction if needed.
4. Add DeepSeek provider and tests.
5. Add source registry and source discovery.
6. Add source ranking and credibility scoring.
7. Add X.com connector behind disabled-by-default config.
8. Add claim extraction and corroboration.
9. Add event clustering and deduplication.
10. Update final report generation schema.
11. Add notification gate.
12. Update UI to show concise report cards.
13. Add tests.
14. Update docs.
15. Run formatters, tests, and basic app smoke test.
16. Produce a concise handoff summary.

---

## Important Quality Bar

Do not implement this as a messy one-file patch.

Keep modules clean and testable.

Prefer small pure functions for:

- source ranking
- claim extraction normalization
- event similarity scoring
- confidence scoring
- notification gating

Use typed data models where possible.

All external API clients must be isolated behind adapters.

No real network calls in unit tests.

No secrets in repo.

No broken placeholders.

No raw stack traces in browser UI.

When uncertain, choose a stable modular foundation over a quick hack.

---

## Final Output Required From Codex

After completing the work, provide:

1. Summary of changed files.
2. Explanation of new architecture.
3. How to configure DeepSeek.
4. How to configure X.com.
5. How source discovery works.
6. How credibility scoring works.
7. How event clustering works.
8. Tests added and test results.
9. Remaining limitations.
10. Recommended next version tasks.
