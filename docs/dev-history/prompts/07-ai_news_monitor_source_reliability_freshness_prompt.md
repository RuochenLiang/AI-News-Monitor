# AI News Monitor — Source Reliability, Freshness & Intelligence Gaps Upgrade Prompt

## Codex CLI command

Place this file in the repository root, then run Codex CLI from the repository root:

```text
/goal Read ./ai_news_monitor_source_reliability_freshness_prompt.md carefully and implement everything described in it. Treat this file as the authoritative specification for the next iteration. Before coding, read CHATBOT_CONTEXT.md, HANDOFF.md, README.md, README.zh-CN.md, SOURCE_GUIDE.md, NOTIFICATION_GUIDE.md, docs/RELEASE_CHECKLIST.md, config.example.yaml, src/, tests/, locales/, and .github/workflows/. Do not assume real API keys, real Gmail credentials, real webhook tokens, or real runtime data. Do not copy code, assets, data, or text from external projects. Only use architectural ideas. Focus on source reliability, freshness states, intelligence gaps, source caching, smart polling/backoff, and source-package presets while keeping the app lightweight and public-GitHub-ready. Keep source code English-only, keep Chinese only in locale/documentation resources, run tests after each milestone, and finish with a requirement-by-requirement audit.
```

---

## Context

The current AI News Monitor is close to a public GitHub release candidate. It already has:

- Local-first 24/7 monitoring
- Browser/local console
- Fast Alert default mode
- Source library
- Multiple notifiers
- Diagnostics
- Chinese/English i18n
- GPL-3.0-only license
- AI-assisted development disclosure
- GitHub Actions
- Release checklist

The next improvement should **not** add unrelated features. The goal is to improve the core reason this product exists:

> A reliable 24/7 information radar that pulls from enough high-quality Chinese and English public sources, understands which sources are trustworthy and fresh, detects when coverage is weak or stale, and sends the user timely high-quality alerts.

This iteration is inspired by public architectural ideas from mature monitoring systems, but the project must **not copy external project code, UI, data, feed lists, docs, or assets**.

---

# Non-negotiable rules

## 1. Do not copy external project code or data

Do not copy code, feed lists, UI, documentation wording, assets, schemas, or proprietary implementation details from external repositories.

It is acceptable to implement original code based on high-level ideas such as:

- Source tiering
- Source freshness states
- Intelligence gap reporting
- Last-known-good cache
- Smart polling/backoff
- Source package presets
- Health dashboards

## 2. Source code English-only

All source code must remain English-only.

This includes:

- Python source
- Tests
- Scripts
- GitHub Actions
- Comments
- Docstrings
- Embedded HTML/CSS/JS
- UI string keys in code

Chinese text is allowed only in:

- `locales/zh-CN.*`
- `README.zh-CN.md`
- Chinese documentation resources

Do not hard-code Chinese UI text in source code.

## 3. No real secrets or private runtime data

Do not add or assume real:

- API keys
- Webhooks
- Gmail app passwords
- SMTP credentials
- Telegram tokens
- WeCom keys
- WeChat/QQ relay keys
- Personal emails
- Real user prompts
- Real runtime data

Tests must use mocks, local fake services, monkeypatching, or placeholders.

## 4. Keep it lightweight

Avoid heavy dependencies and architectural rewrites. Prefer:

- Existing Python architecture
- Existing local server/browser console
- Existing PySide integration if present
- Existing source/notifier abstractions
- Small, testable modules
- Lightweight data structures
- SQLite/local storage if needed
- No mandatory cloud infrastructure

## 5. Preserve public GitHub readiness

Keep or improve:

- GPL-3.0-only license
- README language switching
- AI_DISCLOSURE.md
- SECURITY.md
- CONTRIBUTING.md
- SOURCE_GUIDE.md
- NOTIFICATION_GUIDE.md
- docs/RELEASE_CHECKLIST.md
- GitHub Actions
- No committed secrets
- No proprietary fonts/assets

---

# Main objective

Implement a **Source Reliability, Freshness & Intelligence Gaps Upgrade**.

The app should tell the user not only:

```text
Here are matching articles.
```

but also:

```text
Which source tier did they come from?
Are the important source groups fresh?
Which source groups are stale or failing?
Is this event confirmed by multiple independent sources?
Is the current topic coverage strong or weak?
Which sources are missing, empty, or degraded?
```

---

# Workstream A — Source Tiering and Reliability Metadata

## Goal

Make source quality explicit and easy to understand.

## Requirements

Add or extend source metadata with:

```yaml
source_tier: 1          # 1, 2, 3, or 4
source_role: "official" # official | wire | major_media | niche_media | company_ir | aggregator | blog | custom
state_affiliated: false
propaganda_risk: "low" # low | medium | high | unknown
editorial_context: ""
```

## Tier definitions

Use these definitions in docs and UI:

```text
Tier 1: Official, primary, wire, or direct company/organization sources.
Tier 2: Major mainstream media or well-established financial/technology media.
Tier 3: Specialist, niche, local, or domain-specific sources.
Tier 4: Aggregators, blogs, repost-heavy sources, or low-confidence custom sources.
```

## Source scoring integration

Update scoring so source tier and role influence ranking:

- Tier 1 should receive the strongest reliability boost.
- Official and company IR sources should receive role-specific boosts.
- Tier 4 and aggregator/blog sources should receive lower default trust.
- State affiliation and propaganda risk should not automatically block a source, but should be visible and may lower trust if configured.
- User whitelist/blacklist must still override normal scoring rules where configured.

## UI requirements

Source cards should show:

- Tier badge
- Role badge
- State-affiliated indicator if true
- Propaganda risk indicator
- Reliability score
- Explanation tooltip/help text

Example user-facing context:

```text
Tier 1 · Official source · High reliability
```

or:

```text
Tier 4 · Aggregator · Use with caution
```

## Config requirements

Update `config.example.yaml` and source library entries to include these fields where appropriate.

Do not require users to fill all fields for custom sources. Provide defaults:

```yaml
source_tier: 4
source_role: "custom"
propaganda_risk: "unknown"
state_affiliated: false
```

## Tests

Add tests for:

- Source tier parsing.
- Default metadata for custom sources.
- Tier-based scoring.
- Official/company IR boost.
- Tier 4 lower trust.
- UI/status serialization of tier metadata.

---

# Workstream B — Source Freshness States

## Goal

Make source health and freshness clear.

## Freshness states

Implement these source states:

```text
fresh
stale
very_stale
no_data
error
disabled
unknown
```

Suggested meanings:

```text
fresh: source succeeded recently within configured freshness window
stale: source has not succeeded recently but is not critically old
very_stale: source has not succeeded for a long time
no_data: source request succeeded but returned no usable articles
error: source request failed
disabled: source is disabled
unknown: no test/fetch history yet
```

## Configurable thresholds

Add config defaults:

```yaml
source_health:
  fresh_within_minutes: 30
  stale_after_minutes: 120
  very_stale_after_minutes: 360
  max_consecutive_failures_before_degraded: 3
```

## Source health fields

For each source, track:

- Last fetch time
- Last success time
- Last failure time
- Last error category
- Last error message
- Consecutive failures
- Last returned article count
- Average fetch latency if practical
- Freshness state

Persist this state locally where appropriate so the dashboard remains useful across restarts.

## UI requirements

In Source Library and Dashboard, show:

- Freshness badge
- Last success time
- Consecutive failures
- Last returned article count
- Failure reason
- Test source button

Use clear status colours:

- Fresh: calm green/blue
- Stale: amber
- Very stale/error: red/orange
- No data: grey
- Disabled: muted

Keep colours accessible and not overly harsh.

## Tests

Add tests for:

- Fresh state.
- Stale state.
- Very stale state.
- No-data state.
- Error state.
- Disabled state.
- Threshold configuration.
- Persistence/serialization where implemented.

---

# Workstream C — Intelligence Gaps Panel

## Goal

Show the user where coverage is weak, stale, or failing.

This prevents the user from misinterpreting silence as “no news”.

## Definition

An intelligence gap means:

```text
A source category, source package, or topic-critical source group is disabled, stale, empty, or failing in a way that reduces monitoring confidence.
```

## Required gap groups

Compute gaps by:

- Source package
- Source category
- Topic-relevant category
- Language
- Official/government sources
- Finance sources
- China/Taiwan sources
- Semiconductor/AI sources
- Company IR sources

## UI requirements

Add an **Intelligence Gaps** card/panel to the Dashboard and local browser console.

Show:

- Healthy groups
- Degraded groups
- Critical gaps
- Reason
- Recommended action

Examples:

```text
Official/Government sources: degraded — 2 enabled sources are stale.
China/Taiwan sources: critical — no enabled sources returned data in the last 6 hours.
Semiconductor/AI sources: healthy — 5 fresh sources.
```

## Notification behavior

Do not spam gap notifications by default. However, allow optional local dashboard warnings.

Optional config:

```yaml
intelligence_gaps:
  enabled: true
  notify_on_critical_gap: false
  critical_gap_cooldown_minutes: 360
```

## Tests

Add tests for:

- Healthy group.
- Degraded group.
- Critical gap.
- Disabled category.
- Language-specific gap.
- Topic-relevant gap.
- Gap summary serialization.

---

# Workstream D — Source Cache and Last-Known-Good Fallback

## Goal

Make fetch cycles resilient when some sources fail.

## Requirements

Implement source-level caching:

```yaml
source_cache:
  enabled: true
  source_ttl_seconds: 600
  digest_ttl_seconds: 900
  last_known_good_enabled: true
  last_known_good_max_age_hours: 24
```

## Behavior

For each source:

1. If cache is fresh, reuse cached entries where appropriate.
2. If fetch succeeds, update cache and last-known-good.
3. If fetch fails but last-known-good is available and not too old, return cached entries with a degraded marker.
4. Do not treat last-known-good entries as fresh.
5. Clearly mark cached/degraded items in diagnostics and dashboard.
6. Avoid duplicate alerts from cached data.

## Alert behavior

Cached last-known-good articles should generally not generate new alerts unless:

- They were never alerted before.
- The user explicitly enables cached fallback alerting.
- They are within acceptable age thresholds.

Default should avoid stale alert spam.

Suggested config:

```yaml
source_cache:
  allow_cached_alerts: false
```

## Tests

Add tests for:

- Cache hit.
- Cache miss.
- Fetch success updates cache.
- Fetch failure uses last-known-good.
- Expired last-known-good is not used.
- Cached articles do not generate duplicate alerts.
- Diagnostics show degraded cached state.

---

# Workstream E — Smart Polling and Backoff

## Goal

Make 24/7 monitoring more stable by adapting to failures.

## Requirements

Implement source-level polling backoff:

```yaml
smart_polling:
  enabled: true
  failure_backoff_multiplier: 2.0
  max_backoff_minutes: 60
  reset_after_success: true
```

Behavior:

- If a source fails repeatedly, increase its next fetch delay.
- If a source succeeds, reset its backoff.
- Do not let one failing source block the entire monitoring cycle.
- Keep per-source timeout.
- Keep an overall cycle deadline if practical.
- Record current backoff state in source health.

## Suggested fetch limits

Add or preserve sensible defaults:

```yaml
fetching:
  per_source_timeout_seconds: 8
  overall_cycle_deadline_seconds: 40
  max_articles_per_source: 10
  max_candidate_articles_per_topic: 5
```

## UI requirements

Source cards should show if a source is in backoff:

```text
Backoff active · next retry in 12 minutes
```

## Tests

Add tests for:

- Backoff increases after failures.
- Backoff resets after success.
- Source in backoff is skipped until next retry.
- Failing source does not block healthy source.
- Overall cycle still completes.

---

# Workstream F — Multi-Source Confirmation Boost

## Goal

Increase trust when multiple independent sources report the same event.

## Requirements

Improve or add event clustering for scoring.

Use lightweight methods only:

- Normalized title similarity
- Shared entities/keywords
- Same date/time window
- Same topic
- Source independence
- Optional LLM confirmation only if already available and cost-controlled

Do not create heavy embedding/vector dependencies unless already present and justified.

## Scoring

Add or improve:

```yaml
quality:
  multi_source_confirmation_boost: 0.15
  independent_source_bonus: 0.05
  same_owner_confirmation_penalty: 0.05
```

Behavior:

- If multiple independent sources report the same event, boost confidence.
- If sources are from the same owner/network, reduce confirmation strength.
- If one source is official and another is reputable media, boost more.
- Show explanation in alert:

```text
Confirmed by 3 sources: Official source + 2 major media sources.
```

## Tests

Add tests for:

- Same-event cluster detection.
- Independent sources boost.
- Same-owner penalty.
- Official + media confirmation.
- Alert explanation includes confirmation context.

---

# Workstream G — Source Package Presets

## Goal

Make source configuration easier and more relevant to monitoring goals.

## Existing packages

Preserve existing source packages if present.

Add/improve these presets:

- Global News Starter
- Finance Starter
- Official/Government Starter
- China/Taiwan Starter
- US Policy Starter
- Semiconductor/AI Starter
- Company IR Starter
- Taiwan + Semiconductor + Official Sources
- Geopolitics Starter
- AI Industry Starter

## Preset behavior

Each preset should define:

- Recommended sources
- Recommended categories
- Suggested source tier weights
- Suggested refresh interval
- Suggested relevance threshold
- Optional topic starter examples

Do not force-enable everything. Let users preview and apply.

## UI requirements

Add source preset cards:

- Preset name
- Description
- Number of sources
- Expected coverage
- Recommended use case
- Apply/preview button

## Tests

Add tests for:

- Preset parsing.
- Applying a preset.
- Preset does not overwrite unrelated custom settings.
- Preset source count and categories.

---

# Workstream H — Coverage Quality Score

## Goal

Give the user a high-level confidence indicator for whether the current monitor coverage is reliable.

## Requirements

Add a coverage quality score per topic and/or globally.

Inputs:

- Fresh source count
- Enabled source count
- Tier 1/2 source availability
- Category coverage
- Language coverage
- Consecutive failures
- Intelligence gaps
- Recent article volume

Output:

```text
coverage_quality: high | medium | low | critical
```

Examples:

```text
High: 8 fresh sources, 3 Tier 1 sources, no critical gaps.
Medium: Some stale sources but adequate coverage.
Low: Few fresh sources or missing a critical category.
Critical: No fresh sources for key categories.
```

## UI requirements

Dashboard should show:

- Global coverage quality
- Per-topic coverage quality if feasible
- Main reason for score
- Recommended action

## Tests

Add tests for:

- High coverage.
- Medium coverage.
- Low coverage.
- Critical coverage.
- Reason generation.

---

# Workstream I — Dashboard and Local Console Updates

## Goal

Surface reliability and freshness clearly in the operator UI.

## Dashboard additions

Add or improve:

- Source freshness summary
- Intelligence gaps panel
- Coverage quality score
- Source backoff summary
- Last-known-good/cached usage summary
- Multi-source confirmation summary for recent alerts
- Source tier distribution
- Top failing sources

## Local console endpoints

Add or improve JSON endpoints if practical:

```text
/source-health
/intelligence-gaps
/coverage-quality
/source-packages
```

Keep endpoints local-only by default.

## UI style

Keep the design:

- Lightweight
- Apple-like
- Low-glare
- Modular
- Readable
- English/Chinese i18n through locale resources only

## Tests

Add endpoint tests where feasible.

---

# Workstream J — Documentation Updates

Update:

- `README.md`
- `README.zh-CN.md`
- `SOURCE_GUIDE.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/RELEASE_CHECKLIST.md`
- `config.example.yaml`

## Document

- Source tiers
- Source roles
- Propaganda/state-affiliation indicators
- Fresh/stale/very stale/no data/error states
- Intelligence gaps
- Last-known-good cache
- Smart polling/backoff
- Source presets
- Coverage quality
- Multi-source confirmation
- Limitations and non-goals

## Important disclaimer

Keep documentation clear that:

- The app monitors public information sources.
- It does not bypass paywalls.
- It does not simulate login.
- It does not scrape private sources.
- It does not provide financial advice.
- It does not execute trades.

---

# Workstream K — Tests and Release Readiness

## Required tests

Add or update tests for:

1. Source tier metadata parsing.
2. Source role metadata parsing.
3. Source freshness state computation.
4. Intelligence gap detection.
5. Source cache hit/miss.
6. Last-known-good fallback.
7. Cached article no-alert default behavior.
8. Smart polling backoff increase/reset.
9. Failing source does not block healthy source.
10. Multi-source confirmation boost.
11. Same-owner confirmation penalty.
12. Source preset parsing/apply behavior.
13. Coverage quality score.
14. Dashboard/local endpoint serialization.
15. i18n keys for new UI strings.
16. No Chinese in source code.
17. Config example parses.
18. Existing notification/LLM/source diagnostics still pass.
19. GitHub Actions still pass.

## Manual release checklist

Update `docs/RELEASE_CHECKLIST.md` with manual checks for:

- Source freshness panel.
- Intelligence gaps panel.
- Source package presets.
- Source backoff.
- Cached/last-known-good behavior.
- Coverage quality score.
- Multi-source confirmation explanation.

---

# Final audit format

At completion, output:

```text
## Completed
- ...

## Partially completed
- ...

## Not completed / blocked
- ...

## Source reliability changes
- ...

## Freshness and gap tracking
- ...

## Cache and backoff
- ...

## Multi-source confirmation
- ...

## Source presets
- ...

## UI/dashboard changes
- ...

## Tests run
- ...

## Documentation updated
- ...

## Remaining risks
- ...

## Recommended next step
- ...
```

---

# Definition of done

This iteration is complete only when:

- Source tiering exists and affects scoring.
- Source freshness states exist and are visible.
- Intelligence gaps are computed and shown.
- Source cache and last-known-good fallback are implemented or clearly scaffolded.
- Smart polling/backoff works.
- Multi-source confirmation boosts high-quality alerts.
- Source presets are easier to apply.
- Coverage quality score exists.
- Dashboard/local console surfaces all reliability states.
- Documentation explains the new concepts.
- Tests cover the new behavior.
- Source code remains English-only.
- No secrets are committed.
- The project remains lightweight and public-GitHub-ready.
