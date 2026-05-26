# Social Sources

Social media is optional and disabled by default. X.com support is designed as an early signal source, not a verification source.

```yaml
social_sources:
  x:
    enabled: false
    bearer_token_env: X_BEARER_TOKEN
    max_posts_per_topic_per_run: 25
    include_retweets: false
    trusted_accounts: []
    blocked_accounts: []
```

Set `X_BEARER_TOKEN` locally if you enable X.com. Recent search access can cost money and may be rate limited by X.com.

In the desktop app, open Settings -> Sources -> X.com Social Source to enable X recent search, paste the bearer token into the local `.env` field, tune per-topic read caps, account filters, recent-search window, and the cost guard.

If X.com is the only evidence for an event, the notification gate labels the report as an unconfirmed social-media signal. Do not treat it as verified until primary or reputable secondary sources corroborate it.

X.com is queried only when all of these are true:

- `social_sources.x.enabled: true`
- the topic has `social_enabled: true`
- the topic uses `source_mode: auto` or `source_mode: hybrid`
- `X_BEARER_TOKEN` is available locally

The adapter uses official recent-search API calls. It does not scrape logged-in pages, private posts, paywalled views, or restricted content. Posts are normalized into low-confidence social articles so they can be clustered and checked against higher-confidence sources.

Official X docs for this adapter:

- https://docs.x.com/x-api/posts/search/quickstart/recent-search
- https://docs.x.com/x-api/posts/recent-search

Cost controls:

- keep `max_posts_per_topic_per_run` small
- set `trusted_accounts` for narrow monitoring
- keep `include_retweets: false` unless retweets are intentionally useful
- review `cost_guard.daily_max_read_posts`

The X adapter enforces the configured daily read-post guard in memory for the running app session. Once the guard is exhausted, X recent search is skipped until the next UTC day or app restart. This is a safety cap, not a substitute for reviewing X.com plan limits and billing.

Example topic:

```yaml
topics:
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
