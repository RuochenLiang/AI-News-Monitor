# Release Checklist

Use this before publishing a public GitHub release.

## Required Local Checks

- Install dependencies with `python -m pip install -r requirements.txt -r requirements-dev.txt`.
- Run `python -m ruff check .`.
- Run `python -m black --check .`.
- Run `python -m pytest -q`.
- Run `python -m pytest --cov=src --cov-report=term-missing -q`.
- Run `python -m compileall src tests`.
- Run `python -c "from pathlib import Path; from src.config import load_config; load_config(Path('config.example.yaml'), load_env=False)"`.
- Run `python -m ai_news_monitor doctor --check-llm --config config.example.yaml --json` and confirm missing local secrets are reported without exposing values.
- Run `python -m ai_news_monitor doctor --check-sources --config config.example.yaml --json` with network access only when you are ready to exercise public feeds.
- Run the dependency check with `python -c "from src.dependency_check import assert_runtime_dependencies; assert_runtime_dependencies()"`.
- Confirm source code is English-only except allowed locale/docs resources.
- Confirm no `.env`, `config.yaml`, `user_config.yaml`, logs, data, databases, caches, or secrets are in the release source archive.
- Confirm `.gitignore` excludes runtime status snapshots, generated archives, build output, caches, logs, databases, `.env.*`, and private configs.
- Confirm dependency-check guidance is available by reviewing `src/dependency_check.py` and startup behavior.

## Private GitHub Push Gate

Use a private repo first. Do not make repo public until CI and build artifacts have passed.

1. Install dependencies.
2. Run the dependency check.
3. Launch app.
4. Open local console at `http://127.0.0.1:8765`.
5. Configure LLM with a real user-owned key.
6. Test LLM.
7. Configure Gmail with a Gmail App Password.
8. Test Email.
9. Configure at least one fallback notifier.
10. Run E2E Test Mode.
11. Confirm at least one test alert saved.
12. Confirm notification attempted/succeeded or document it as not configured.
13. Run Run Once.
14. Confirm Pipeline Funnel is visible.
15. Confirm `/health`.
16. Confirm `/readiness`.
17. Confirm no raw JSON/URL overflow appears in browser cards.
18. Enable source packages.
19. Test enabled sources.
20. Create a production topic.
21. Start monitoring.
22. Confirm logs do not reveal secrets.
23. Run tests.
24. Confirm GitHub Actions pass after private repo push.
25. Confirm Windows artifact from Actions.
26. Make repo public only after CI/build pass.

## Interface Diagnostics

- LLM diagnostics show required fields, API-key status, model/base URL checks, models endpoint result when available, chat completions test result, category, redacted technical detail, and suggested fix.
- Gmail/SMTP diagnostics validate sender username, app password, From address, recipients, host, port, STARTTLS, authentication, sender/recipient rejection, provider blocks, and timeouts.
- Telegram, WeCom, WeChat Relay, QQ Relay, and Generic Webhook diagnostics show required fields, URL/token status, test result, category, redacted detail, suggested fix, fallback priority, and help link.
- Source diagnostics cover GDELT, Google News RSS, Yahoo Finance RSS, public RSS, official RSS, source-library feeds, and custom RSS/Atom feeds.
- GDELT diagnostics cover both production-shaped topic queries and a simple smoke query, including non-JSON response classification, 429 classification, long-query classification, and redacted previews.
- Yahoo Finance 429 responses are classified as `api_rate_limited`, source backoff is visible, and Finance Starter has alternative public finance sources.
- Source cards show tier, role, state-affiliation, propaganda-risk, reliability, freshness state, last success, consecutive failures, article count, cache status, and backoff state.
- Intelligence gaps are visible for source packages, categories, languages, topic-relevant categories, official/government, finance, China/Taiwan, Semiconductor/AI, and Company IR groups.
- Coverage quality is visible globally and, where available, per topic.
- Source package warnings are visible when no packages are enabled or enabled package sources are not fresh.
- Pipeline funnel is visible after each cycle and shows source counts, deduplicated articles, candidates, event clusters, clusters sent to LLM, LLM decisions, threshold rejections, event alert count, notification attempts, and top rejection reasons.
- Event cluster cards are visible in the browser console with event title, grouped article count, latest update, summary, timeline preview, source links, relation reason, and expandable diagnostics.
- Run Once and E2E Test controls are available in the local browser console; E2E Test is clearly marked as test-only and can verify alert plus mocked/configured notification delivery.
- Run E2E Test and confirm at least one test alert is saved and at least one notification is attempted when a channel is configured.
- Run Run Once and confirm the latest Pipeline Funnel is visible.
- `/health` is documented as liveness only, and `/readiness` or `/api/readiness` summarizes monitor, LLM, notifier, source coverage, critical gaps, last cycle status, and `can_send_alerts`.
- Paused/running/stopped/error state is prominent, including pause reason and next scheduled cycle when available.
- Last-known-good cached fallback is clearly marked as cached/degraded and cached alerting is disabled by default.
- Multi-source event synthesis appears in alert text when multiple independent sources report the same event, including relation reason, timeline, source links, uncertainty, and suggested follow-up.
- Prompt 15 report cards show verification status, relevance score, confidence score, source comparison, timeline, source links, notification status where available, and raw diagnostic details only behind expansion.
- X.com recent-search ingestion is disabled by default and only queried when global X config and the topic's social mode/source mode allow it.
- X.com daily read-post guard is enforced by the adapter for the running app session.
- DeepSeek diagnostics use OpenAI-compatible provider checks and do not rely on deprecated model names.
- DeepSeek/OpenAI-compatible requests honor configured retries and retry backoff before provider fallback is attempted.
- Desktop app can run Test LLM, source tests, and per-channel notification tests without real bundled credentials.
- Desktop Settings page exposes OpenAI/DeepSeek primary/fallback routing, local provider keys, DeepSeek retry fields, and X.com recent-search cost controls.
- Desktop Topics page exposes source mode, domains, preferred regions, social enablement, confidence threshold, and report-style flags.
- Desktop Topics page can preview manual and auto-selected sources with reason, expected value, risk, and priority before a monitoring cycle runs.
- Per-topic report-style flags are honored by LLM prompt preferences and final alert cleanup for timeline, source comparison, and suggested user action sections.
- Browser console remains read-only for configuration, shows concise operator summaries first, keeps raw diagnostics behind details, and wraps long URLs/errors without layout overflow.
- SSE/browser console failures are visible and the local server remains bound to localhost unless LAN access is explicitly enabled.

## User Guidance

- `START_HERE.md` and `START_HERE.zh-CN.md` explain the release-archive path: unzip, open the app, fill LLM/source/topic/notification settings, run tests, and start monitoring.
- `README.md` and `README.zh-CN.md` explain local run steps, Run Once, E2E Test Mode, diagnostics, event clustering, event timelines, pipeline funnel, 0-alert interpretation, readiness vs health, LLM setup, Gmail app passwords, sender vs receiver fields, source testing, and notification testing.
- `NOTIFICATION_GUIDE.md` explains event alert rendering, timelines, source links, Gmail app password setup, SMTP categories, webhook categories, fallback routing, From Address readiness, and pipeline notification failure reasons.
- `SOURCE_GUIDE.md` explains public-source policy, source testing, bulk source diagnostics, GDELT/Yahoo common failures, source package warnings, and website-only candidates.
- `SOURCE_GUIDE.md` explains source tiers, roles, state-affiliation/propaganda-risk context, freshness states, intelligence gaps, source cache, smart polling/backoff, source presets, manual/auto/hybrid source modes, coverage quality, event clustering, timeline date safety, and multi-source confirmation.
- `docs/LLM_PROVIDERS.md`, `docs/SOCIAL_SOURCES.md`, and `docs/VERIFICATION_PIPELINE.md` explain OpenAI/DeepSeek routing, X.com cost/confirmation caveats, and verification gate behavior.
- `config.example.yaml` and `.env.example` contain placeholders only.

## Packaging

- Build macOS with `./scripts/build_macos.sh`.
- Build Windows on Windows or GitHub Actions with `.\scripts\build_windows.ps1`.
- Smoke-test each archive by launching the app with a clean runtime directory.
- Verify release archives include `START_HERE.md`, `START_HERE.zh-CN.md`, `README.md`, `README.zh-CN.md`, `LICENSE`, `AI_DISCLOSURE.md`, `SOURCE_GUIDE.md`, `NOTIFICATION_GUIDE.md`, `config.example.yaml`, `.env.example`, and locale files.

## Manual Sanity Checks

- Open `http://127.0.0.1:8765`.
- Confirm header/nav contrast is readable.
- Confirm font stack uses Apple/System UI fallback.
- Confirm all setup fields have labels and visible focus states.
- Confirm long error text wraps without breaking the layout.
- Confirm the browser console primary cards do not show raw JSON, raw stack traces, or full long URLs by default; verify details/copy diagnostics still expose technical data.
- Confirm Run Once produces a visible pipeline funnel and E2E Test produces a visible `[E2E TEST]` alert path with mock or configured notification delivery.
- Confirm E2E Test produces one event-level alert with a timeline/source section and event-cluster diagnostics.
- Confirm no raw JSON, full encoded GDELT queries, long URLs, or stack traces appear in primary browser cards by default.
- Confirm `LICENSE` exists and project metadata says `GPL-3.0-only`.
- Confirm GitHub Actions pass after upload.
- Confirm the Windows build artifact is produced before publishing a Windows release.
- Confirm no test requires real API keys, Gmail credentials, webhook tokens, or runtime data.
- Confirm source freshness panel, intelligence gaps panel, source package presets, source backoff, cached/last-known-good behavior, coverage quality score, event clusters, timeline preview, source links, and multi-source confirmation explanation are visible in the desktop dashboard or local browser console.
