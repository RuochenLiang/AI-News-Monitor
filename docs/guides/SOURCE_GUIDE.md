# Source Guide

## Source Modes

Topics support `manual`, `auto`, and `hybrid` source modes.

- `manual`: use configured sources only. This is the compatibility default.
- `auto`: select sources from the curated registry based on topic domains.
- `hybrid`: use configured sources first, then add ranked discovered sources.

Auto discovery ranks source candidates by domain fit, credibility hint, source type, and preferred region. Social media sources are excluded unless the topic enables social signals and the corresponding source is configured.

In the desktop app, the Topics page exposes the next-version topic schema: topic ID, source mode, domains, preferred regions, per-topic social enablement, relevance/confidence thresholds, and report-style toggles. Existing configs that omit these fields still run as `source_mode: manual` with social sources disabled.

The Settings > Sources tab also exposes X.com recent-search controls. Keep X disabled unless you have reviewed X.com API access and cost, then enable it globally and enable social sources only on the topics that should use it.

Use **Preview Source Selection** on the Topics page before saving or running the monitor. It shows manual sources for `manual`/`hybrid` topics and ranked auto-selected candidates for `auto`/`hybrid` topics, including selection reason, expected value, risk, and priority.

The browser console Sources page shows a Source Selection panel after a monitoring cycle. For each selected source it shows:

- topic and source mode
- source name and source type
- whether it was manually configured or auto-selected
- selection reason
- expected value
- risk note, when present
- ranking priority for discovered sources

Use this panel to understand why `auto` or `hybrid` added a source. If a source is noisy, disable the source package, add a blacklist entry, or switch the topic back to `manual`.

## Source Doctor

Run a source health check without opening the desktop UI:

```bash
python -m ai_news_monitor doctor --check-sources
```

This checks enabled source adapters with the current config. Some public feeds can rate-limit or fail independently of the app, so treat failures as diagnostics rather than automatic bugs.

If X.com is enabled, the doctor also checks whether `X_BEARER_TOKEN` is configured before any live recent-search fetch is attempted.

AI News Monitor only supports public RSS/Atom feeds, official public feeds, and free public APIs. Do not add paywalled, login-only, private, or unauthorized scraped pages.

## Source Library

The app includes a curated source library with 50+ optional candidates across:

- Global News
- Finance
- Official/Government
- China
- Taiwan
- US
- Semiconductor/AI
- Company IR
- Custom

Only a few high-quality defaults are enabled in `config.example.yaml`. In the desktop app, open Settings > Sources, select a source library item, then use:

- Enable/disable selected
- Test selected source
- Open source website
- RSS/Atom help

Each source can carry language, type, reliability, ownership, bias/context, website URL, and status metadata. Custom sources are persisted in `config.yaml`.

Some library entries are website-only candidates when no currently verified public RSS/Atom feed is available. They remain useful for manual review and source discovery, but the monitor only auto-fetches entries whose type is `rss`.

Built-in source packages:

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

The browser console shows enabled packages, effective enabled source count, fresh source count, included source names, and warnings. If no packages are enabled, treat coverage as incomplete until at least one package or custom source is enabled. If a package is enabled but none of its sources are fresh, test sources, wait for backoff to expire, or add another package.

For broad topics, set `domains` explicitly when possible. The classifier can infer domains from the topic text, but explicit domains make source selection easier to review:

```yaml
source_mode: hybrid
domains:
  - politics
  - public_policy
  - semiconductor
preferred_regions:
  - US
  - Taiwan
social_enabled: false
```

## Source Tiers and Roles

AI News Monitor uses source metadata to make ranking and operator confidence easier to inspect:

- Tier 1: official, primary, wire, or direct company/organization sources.
- Tier 2: major mainstream media or well-established financial/technology media.
- Tier 3: specialist, niche, local, or domain-specific sources.
- Tier 4: aggregators, blogs, repost-heavy sources, or low-confidence custom sources.

Roles are `official`, `wire`, `major_media`, `niche_media`, `company_ir`, `aggregator`, `blog`, or `custom`. State-affiliation and propaganda-risk indicators are visible context only; they do not automatically block a source. Whitelist and blacklist settings still override normal scoring behavior.

Custom sources default to:

```yaml
source_tier: 4
source_role: "custom"
state_affiliated: false
propaganda_risk: "unknown"
```

## Freshness, Gaps, Cache, and Backoff

Freshness states are:

- `fresh`: recent successful data within the configured window.
- `stale`: a source has not succeeded recently.
- `very_stale`: a source has not succeeded for a long time.
- `no_data`: the source was reachable but returned no usable articles.
- `error`: the request failed.
- `disabled`: the source is not enabled.
- `unknown`: no fetch or test history exists yet.

The dashboard and browser console compute intelligence gaps by source package, category, topic-relevant category, language, official/government coverage, finance coverage, China/Taiwan coverage, Semiconductor/AI coverage, and Company IR coverage. A gap means silence may reflect weak or stale monitoring coverage rather than no news.

Source cache is local-only. Fresh cache can avoid repeat fetches during short cycles. Last-known-good fallback can keep diagnostics useful when a source fails, but cached fallback articles are marked degraded and do not generate new alerts by default. Smart polling increases per-source backoff after repeated failures and resets after success so one failing source does not block healthy sources.

## Coverage Quality and Confirmation

Coverage quality summarizes confidence as `high`, `medium`, `low`, or `critical` using fresh source count, enabled source count, Tier 1/2 availability, category/language coverage, failures, intelligence gaps, and recent article volume.

Multi-source confirmation boosts ranking when several independent sources report the same event. Related articles are now grouped into event clusters before final LLM synthesis when they share important topic terms, entities, source context, and publication-time proximity. Confirmation is weaker when reports appear to come from the same owner or network. Alerts include the relation reason, source list, and confirmation context when available.

Event timelines are generated only from source metadata and provided article text. Exact source-mentioned dates such as `2026-05-25` or `May 25, 2026` can become timeline items; partial dates stay in the description instead of inventing a year. If the app only has article publication time, the timeline item is labeled as publication-time based. If no date exists, the date stays `unknown`; the app should not invent event dates. For topics where timing matters, prefer official/government, company IR, wire, or other primary sources in the enabled source package.

## Custom Source Rules

Use a public feed URL such as:

```text
https://example.com/feed.xml
https://example.com/rss
https://example.com/atom.xml
```

Set reliability from `0` to `1`. Official government or company feeds should generally be higher than anonymous aggregators. If a source has known ownership or framing context, fill those fields so alerts can explain why the article was selected.

Unsupported source types:

- Paywalled articles that require login
- Browser-only pages without RSS/Atom/API access
- Private Slack/Discord/email/newsletter content without explicit permission
- Scraping pages that block or prohibit automated access

## Testing

Use the source test button before enabling a new feed. A valid feed should return at least one entry and show sample titles.

Use **Test Enabled Sources** after changing packages or custom feeds. The browser console reports a per-source result with:

- Required fields and missing fields.
- Last test status, latency, and sample titles when available.
- Error category such as `invalid_url`, `api_rate_limited`, `api_bad_response`, `query_too_long`, `unsupported_query_shape`, `invalid_encoded_query`, `feed_unreachable`, `feed_parse_failed`, `feed_empty`, `api_timeout`, `tls_or_certificate_error`, `network_unreachable`, or `proxy_or_firewall_issue`.
- A suggested fix and redacted technical detail.

GDELT is checked as a public JSON API with two diagnostics: the same production-shaped topic query builder used by monitoring, and a simple smoke query. Non-JSON responses are classified without calling JSON parsing blindly, and only a short redacted preview is retained. Long or malformed GDELT queries are reported as `query_too_long`, `unsupported_query_shape`, or `invalid_encoded_query`; reduce keywords, use fewer OR terms, or rely on Google News RSS fallback.

Google News RSS, Yahoo Finance RSS, public RSS, official RSS, source-library feeds, and custom RSS/Atom feeds are checked as feed URLs. Yahoo Finance HTTP 429 responses are classified as `api_rate_limited`, put into source backoff, and shown as a concise rate-limit status instead of raw HTTP text. Finance Starter includes multiple public finance sources so monitoring is not dependent on one rate-limited Yahoo feed. Website-only candidates are for manual review and are not auto-fetched until a verified public feed/API URL is configured.
