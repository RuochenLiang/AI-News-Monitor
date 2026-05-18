# AI News Monitor

[简体中文](README.zh-CN.md)

AI News Monitor is a local-first desktop app and temporary local server for monitoring public Chinese and English news sources. It ranks source-grounded articles against user topics, uses the user's OpenAI-compatible LLM for translation, summaries, relevance checks, and optional analysis, then sends timely alerts through phone-friendly channels.

This project is not a trading bot, broker integration, stock recommender, or investment adviser. Alerts are AI-assisted information monitoring output; verify source links before acting on them.

## License and AI Disclosure

AI News Monitor is released under `GPL-3.0-only`. See [LICENSE](LICENSE).

This project was developed with AI assistance. AI-assisted code, documentation, and tests should be reviewed, tested, and maintained by the project owner or contributors before release. See [AI_DISCLOSURE.md](AI_DISCLOSURE.md).

## Security

Do not commit `.env`, `config.yaml`, `user_config.yaml`, `data/`, `logs/`, SQLite databases, API keys, SMTP credentials, webhook URLs, Telegram tokens, chat IDs, or private prompts. The repository only includes `.env.example` and `config.example.yaml` placeholders.

## Development Prompt Archive

The markdown file [docs/dev-history/prompt.md](docs/dev-history/prompt.md) consolidates the given development prompts used while building and preparing this project for release. It is project history, not a file required for normal installation or use.

Ordered prompt archive:

1. [Initial AI News Monitor prompt](docs/dev-history/prompt.md#01-initial-ai-news-monitor-prompt)
2. [Next-phase product prompt](docs/dev-history/prompt.md#02-next-phase-product-prompt)
3. [Update prompt](docs/dev-history/prompt.md#03-update-prompt)
4. [Next-iteration prompt](docs/dev-history/prompt.md#04-next-iteration-prompt)
5. [Final target candidate prompt](docs/dev-history/prompt.md#05-final-target-candidate-prompt)
6. [Pre-GitHub interface stabilization prompt](docs/dev-history/prompt.md#06-pre-github-interface-stabilization-prompt)
7. [Source reliability and freshness prompt](docs/dev-history/prompt.md#07-source-reliability-and-freshness-prompt)
8. [GitHub upload readiness prompt](docs/dev-history/prompt.md#08-github-upload-readiness-prompt)
9. [E2E operational closure prompt](docs/dev-history/prompt.md#09-e2e-operational-closure-prompt)
10. [Final GitHub upload cleanup prompt](docs/dev-history/prompt.md#10-final-github-upload-cleanup-prompt)
11. [Phase verification prompt](docs/dev-history/prompt.md#11-phase-verification-prompt)

## Quick Start on macOS

Install Python 3.11, then run:

```bash
cd "/path/to/AI-News-Monitor"
./scripts/run_macos.sh
```

The script creates the virtual environment at `~/.venvs/ai-news-monitor` when needed, installs dependencies, and starts the app.

The local browser console starts at:

```text
http://127.0.0.1:8765
```

Health and machine-readable status:

```text
http://127.0.0.1:8765/health
http://127.0.0.1:8765/readiness
http://127.0.0.1:8765/status
http://127.0.0.1:8765/events
```

`/health` only means the local HTTP server is alive. `/readiness` summarizes whether monitoring is actually ready: monitor state, LLM readiness, notification readiness, source coverage, critical gaps, last cycle status, and whether alerts can be sent.

## Quick Start on Windows

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## First Run

On first launch, the app creates local runtime files in the application data directory unless `config.yaml` or `.env` already exists next to the executable.

- macOS: `~/Library/Application Support/AI News Monitor/`
- Windows: `%APPDATA%/AI News Monitor/`

Use the desktop app Settings, Sources, Topics, and Notifications pages to configure before starting monitoring:

- LLM API key, model, and OpenAI-compatible base URL
- At least 1 topic with keywords or broad search enabled
- Source packages or custom RSS/Atom feeds
- At least 1 notification channel
- Fast Alert or Full Analysis mode

The browser console at `http://127.0.0.1:8765` is read-only and is intended for live monitoring status, readiness, pipeline funnel, source health, notification state, concise events, logs, and recent alerts. It has Run Once and E2E Test controls, but configuration and credential entry stay in the desktop app. Advanced users can still edit `config.yaml` and `.env` directly in the local runtime directory.

## Diagnostics and Test Buttons

Use the desktop app before starting a long monitoring session:

- Settings > LLM Settings > Test LLM checks required fields, API key authentication, the provider models endpoint when available, and the chat completions endpoint.
- Sources > Test Selected Source checks RSS/Atom feeds and supported public source candidates.
- Notifications > Test sends one test message through the selected channel and reports the failure category, suggested fix, redacted technical detail, and missing fields.
- Browser console > Run Once triggers one real monitoring cycle immediately.
- Browser console > E2E Test runs a controlled local fixture marked `[E2E TEST]` so the fetch -> candidate -> LLM -> alert -> notification chain can be verified without depending on live news.

Standard failure categories include `missing_required_field`, `invalid_url`, `invalid_email_address`, `invalid_api_key`, `model_not_found`, `unsupported_model_api`, `base_url_unreachable`, `api_auth_failed`, `api_rate_limited`, `api_timeout`, `api_bad_response`, `query_too_long`, `unsupported_query_shape`, `invalid_encoded_query`, `tls_or_certificate_error`, `network_unreachable`, `proxy_or_firewall_issue`, `smtp_auth_failed`, `smtp_starttls_failed`, `smtp_sender_rejected`, `smtp_recipient_rejected`, `smtp_connection_timeout`, `smtp_provider_blocked`, `webhook_unreachable`, `webhook_http_error`, `webhook_auth_failed`, `feed_unreachable`, `feed_parse_failed`, `feed_empty`, `source_language_unsupported`, `local_server_port_in_use`, `sse_connection_failed`, and `unknown_error`.

## Pipeline Funnel and Zero Alerts

Every cycle records a concise funnel, for example:

```text
Fetched 441 -> Language 390 -> Keyword 12 -> New 3 -> LLM 2 -> Alerts 0
```

If there are 0 alerts, the dashboard explains the first major blocker: no keyword match, duplicate, unsupported language, LLM rejected, below threshold, cooldown, rate limit, missing notifier, or notification failure. Below-threshold cycles show the top rejected candidate score and the topic threshold. For E2E checks, use E2E Test or temporarily lower only the test threshold to around 50-60; keep production thresholds high enough to reduce noise.

## LLM Settings

Recommended OpenAI-compatible defaults:

- `base_url`: `https://api.openai.com/v1`
- `temperature`: `0.7`
- `top_p`: `1.0`
- `presence_penalty`: `0.0`
- `max_tokens`: `1024`
- `timeout_seconds`: `30`

Regular users usually need only:

- Model name, for example `gpt-4.1-mini`
- API key from the LLM provider console

The API key is stored locally in `.env` as `LLM_API_KEY`, not in source code.

If the LLM test fails:

- `invalid_api_key`: create or copy a fresh key from the provider console.
- `model_not_found`: copy the exact model id from the provider's model list.
- `base_url_unreachable` or `network_unreachable`: check the base URL, VPN, proxy, firewall, and provider status.
- `unsupported_model_api`: use an OpenAI-compatible `/chat/completions` endpoint or choose a supported provider/model.

## Alerts

Fast Alert is the default. It includes:

- Original title and link
- Translated title when needed
- Source and published time
- Short summary
- Match reason and keywords/entities
- Source context and reliability
- Multi-source event cluster context
- Quality and relevance explanation

Full Analysis is optional and includes deeper LLM fields such as why-it-matters, scenarios, risk notes, and uncertainty.

## Source Library

The app ships with a curated optional public source library and source packages:

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

Only use public RSS/Atom feeds or free public APIs. Do not add paywalled, login-only, private, or unauthorized scraped sources. See [SOURCE_GUIDE.md](SOURCE_GUIDE.md).

## Source Reliability and Coverage

Sources now carry explicit reliability metadata:

- Tier 1: official, primary, wire, or direct company/organization sources.
- Tier 2: major mainstream media or established financial/technology media.
- Tier 3: specialist, niche, local, or domain-specific sources.
- Tier 4: aggregators, blogs, repost-heavy sources, or low-confidence custom sources.

Each source can also show a role, state-affiliation indicator, propaganda-risk indicator, editorial context, reliability score, freshness state, consecutive failures, last returned article count, cache status, and smart-polling backoff state.

The dashboard and read-only browser console surface:

- Intelligence gaps: source packages, categories, languages, and topic-relevant groups that are disabled, stale, empty, or failing.
- Coverage quality: `high`, `medium`, `low`, or `critical` confidence for current monitoring coverage.
- Source package state: enabled packages, effective source counts, fresh source counts, and warnings when no package is enabled or enabled package sources are not fresh.
- Last-known-good fallback: stale cached data can keep diagnostics useful when a source fails, but cached articles do not generate new alerts by default.
- Multi-source confirmation: alerts explain when an event is confirmed by multiple independent sources and penalize same-owner confirmation.

GDELT diagnostics now test both a production-shaped topic query and a simple smoke query. Non-JSON responses, long queries, malformed query shapes, 429 rate limits, and timeouts are classified with suggested fixes. Yahoo Finance 429 responses are treated as `api_rate_limited`, trigger source backoff, and should be offset with other public finance sources from Finance Starter.

## Notifications

Supported notification channels:

- Email
- Telegram
- WeCom
- WeChat relay
- QQ relay
- Generic webhook

Notification routing supports retries and fallback order. Third-party relay services receive notification content and links; review their privacy policy and limits before using them. See [NOTIFICATION_GUIDE.md](NOTIFICATION_GUIDE.md).

For Gmail, use `smtp.gmail.com`, port `587`, and STARTTLS. The SMTP username and From address should usually be the sender Gmail address. The recipient field is where alerts are delivered. The From address is required; if it differs from the SMTP username, the app warns because some providers reject unapproved aliases. Gmail normally requires 2-step verification and an app password; your normal Gmail login password will usually fail with `smtp_auth_failed`.

## Development

```bash
./scripts/bootstrap_macos.sh
source "$HOME/.venvs/ai-news-monitor/bin/activate"
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall src tests
```

Optional quality checks:

```bash
python -m ruff check .
python -m black --check .
```

Tests use mocks and do not require real API keys.

If startup reports a missing dependency such as `PySide6` or `feedparser`, use the Python executable shown in the message and run:

```bash
python -m pip install -r requirements.txt
```

## Remote Access

The local server listens on `127.0.0.1` by default. Enable LAN access only on trusted networks. For remote use, prefer SSH tunnels or an authenticated reverse proxy.
