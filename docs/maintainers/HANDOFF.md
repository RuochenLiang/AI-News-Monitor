# Handoff

## Current Goal

Treat `docs/dev-history/prompts/15-intelligent-source-discovery-verification-social-deepseek.md` as the current next-version prompt. It asks for intelligent source discovery with manual/auto/hybrid modes, source credibility and claim verification, multi-source event reports, optional X.com signal ingestion, DeepSeek provider support, generalized topics, concise browser report cards, compatibility migration, tests, and docs.

## Prompt 15 Foundation Pass

- Archived the root-level next-version prompt as `docs/dev-history/prompts/15-intelligent-source-discovery-verification-social-deepseek.md` and updated the prompt archive indexes/readiness test.
- Added backward-compatible topic fields for `source_mode`, domains, preferred regions, social enablement, confidence thresholds, `user_prompt`, nested `notification_threshold`, and report-style flags.
- Added source discovery/ranking modules that classify topics and select ranked source candidates from the existing curated source library for `auto` and `hybrid` modes.
- Added the `src/aggregation/` namespace for event clustering, timeline payloads, and article dedupe while preserving compatibility with the earlier root modules.
- Added source candidate, selected source, social post, source credibility, claim, verification report, and notification gate data models.
- Added a verification package for source credibility scoring, lightweight claim extraction/corroboration, report confidence scoring, and notification gating.
- Added OpenAI/DeepSeek provider config parsing and an LLM router that can fall back across OpenAI-compatible providers while preserving old `openai_compatible` configs. Configured retry backoff is now passed to OpenAI-compatible HTTP retries.
- Added disabled-by-default X.com config plus query builder, normalizer, and API client scaffolding with bearer-token readiness checks.
- Added X.com as an optional `NewsSource` adapter that converts recent-search posts to low-confidence social `Article`s only when global X config is enabled and the topic uses `auto`/`hybrid` source mode with social enabled. Auto source selection now keeps X only for eligible social topics, and the adapter enforces the in-session daily read-post guard.
- Integrated source discovery into the monitor loop for `auto` and `hybrid` topics, and integrated the verification gate before alert notification.
- Extended the desktop Topics page so topic ID, source mode, domains, preferred regions, social enablement, confidence threshold, and report-style flags can be edited without hand-writing YAML.
- Added a desktop topic source-selection preview so manual and auto-selected sources can be reviewed with reason, expected value, risk, and priority before a monitor run.
- Extended the desktop Settings page so OpenAI/DeepSeek primary/fallback routing, provider keys, DeepSeek retry fields, and X.com recent-search/cost-guard settings can be edited without hand-writing YAML.
- Wired per-topic report-style flags into LLM prompt preferences and final alert cleanup so timeline, source comparison, and suggested-action sections can be hidden.
- Added verification status, relevance score, confidence score, and source comparison fields to serialized browser report cards.
- Added contradiction surfacing in claim corroboration and verification report risks.
- Added `python -m ai_news_monitor doctor --check-llm/--check-sources` for non-UI diagnostics.
- Added docs for LLM providers, social sources, and the verification pipeline.
- Added focused tests for source discovery/ranking, claim corroboration, notification gating, DeepSeek fallback, X config/query behavior, report generation inputs, UI raw-output defaults, and prompt archive readiness.

## Event Synthesis Pass

- Added deterministic event clustering before final LLM analysis.
- Tightened clustering so generic broad topic terms such as `AI` are not enough to group unrelated stories from the same feed.
- Added event timeline extraction from publication metadata and exact source-mentioned dates with unknown-date handling.
- Extended LLM structured-output parsing/schema for event title, event summary, current status, why-it-matters, labeled timeline items, key facts, affected entities, source links, relation reason, uncertainties, suggested actions, and `should_notify`.
- Kept single-article compatibility by creating one event cluster for a single candidate.
- Updated alert/notification rendering so Email, Telegram, WeCom, relay, and webhook paths receive readable event alerts with timeline and source links rather than raw JSON.
- Updated browser console status serialization and UI cards to show event clusters, latest update, grouped article count, timeline preview, source list, and relation reason.
- Updated pipeline diagnostics to distinguish fetched articles, deduplicated articles, candidates, event clusters, clusters sent to LLM, event alerts, and notifications.
- Added tests for related/unrelated/single event clustering, chronological timeline safety, event schema parsing, event notification rendering, browser UI event cards, locale keys, and updated E2E funnel counters.

## Completed Work

- Confirmed `LICENSE` exists and contains GPL-3.0-only text.
- Added GPL-3.0-only project metadata in `pyproject.toml`.
- Strengthened `.gitignore` for `.env.*`, runtime configs, `CURRENT_RUNTIME_STATUS.json`, caches, logs, databases, build output, specs, archives, and OS clutter while keeping `.env.example`.
- Removed `CURRENT_RUNTIME_STATUS.json` from the public-upload candidate because it is local runtime data.
- Added `src/dependency_check.py` and startup dependency import validation for PySide6, feedparser, httpx, beautifulsoup4, PyYAML, and python-dotenv.
- Added a macOS Qt plugin cache fallback so copied/quarantined PySide6 plugin files can still load before `QApplication` starts.
- Preserved Run Once and E2E Test Mode from the previous closure work.
- Preserved Pipeline Funnel and expanded rejection categories to include `source_package_disabled` and `coverage_critical`.
- Updated zero-notifier wording so a saved test alert reports: `Alert pipeline succeeded, but no notification channel is ready.`
- Kept `/health` as server liveness and `/readiness`/`/api/readiness` as monitoring readiness.
- Kept browser console concise with overflow-safe CSS and raw diagnostics behind `Show details` / `Copy diagnostics`.
- Added source package serialization fields for failing source count and last package test time.
- Added source package browser-console affordance telling users to enable packages in the desktop app.
- Added or expanded release-readiness tests for dependency checks, secret scans, runtime artifact scans, state document synchronization, workflow commands, public release files, license metadata, and browser console readiness affordances.
- Synchronized `docs/maintainers/CHATBOT_CONTEXT.md`, `docs/maintainers/HANDOFF.md`, `docs/reports/NEXT_VERSION_MONITORING_REPORT.md`, `docs/RELEASE_CHECKLIST.md`, docs, and changelog with the latest E2E/readiness state.
- Moved historical root-level development prompts into `docs/dev-history/prompts/` and added `docs/dev-history/README.md`.
- Prompt archive links now point at standalone numbered files, with `docs/dev-history/prompt.md` retained as a consolidated reference.
- GDELT multi-keyword OR queries are wrapped in parentheses for safer production query syntax.
- E2E Test Mode can be rerun without stored-alert dedupe blocking the controlled second test alert.
- Removed generated local artifacts from the repository root, including cache directories, `.DS_Store`, `.coverage`, and generated zip archives.

## Files Changed In This Readiness Pass

- `.gitignore`
- `pyproject.toml`
- `src/app.py`
- `src/dependency_check.py`
- `src/event_clustering.py`
- `src/event_synthesis.py`
- `src/llm_client.py`
- `src/models.py`
- `src/notifiers/base.py`
- `src/notifiers/generic_webhook_notifier.py`
- `src/pipeline.py`
- `src/realtime.py`
- `src/source_reliability.py`
- `src/sources/gdelt.py`
- `tests/test_app_qt_runtime.py`
- `tests/test_event_browser_ui.py`
- `tests/test_event_clustering.py`
- `tests/test_event_notification_rendering.py`
- `tests/test_e2e_operational_closure.py`
- `tests/test_llm_schema.py`
- `tests/test_release_readiness.py`
- `tests/test_sources.py`
- `docs/maintainers/CHATBOT_CONTEXT.md`
- `docs/maintainers/HANDOFF.md`
- `docs/reports/NEXT_VERSION_MONITORING_REPORT.md`
- `README.md`
- `README.zh-CN.md`
- `docs/guides/SOURCE_GUIDE.md`
- `docs/guides/NOTIFICATION_GUIDE.md`
- `docs/INSTALL.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/RELEASE_CHECKLIST.md`
- `CHANGELOG.md`
- `docs/dev-history/README.md`
- `docs/dev-history/prompt.md`
- `docs/dev-history/prompts/`

## Commands To Run After Resume

```bash
cd "/path/to/AI-News-Monitor"
source .venv/bin/activate
python -m ruff check .
python -m black --check .
python -m pytest -q
python -m pytest --cov=src --cov-report=term-missing -q
python -m compileall src tests
python -c "from pathlib import Path; from src.config import load_config; load_config(Path('config.example.yaml'), load_env=False); print('config ok')"
```

## Latest Known Test Results

Latest local verification on 2026-05-26 after the prompt 15 foundation pass:

- Ruff: `python -m ruff check .` passed.
- Black check: `python -m black --check .` passed; `102 files would be left unchanged`.
- Full pytest: `python -m pytest -q` passed; `140 passed`, `14 skipped`.
- Compileall: `python -m compileall ai_news_monitor src tests` passed.
- `config.example.yaml` parse: `python -c "from pathlib import Path; from src.config import load_config; load_config(Path('config.example.yaml'), load_env=False); print('config ok')"` printed `config ok`.
- `git diff --check` passed.
- `python -m ai_news_monitor doctor --check-llm --config config.example.yaml --json` ran successfully as a command path and returned the expected missing `OPENAI_API_KEY` diagnostic for the placeholder example config.
- Isolated E2E Test Mode with all notifiers disabled produced one event-level alert: `Fetched 1 -> Dedupe 1 -> Candidates 1 -> Events 1 -> LLM 1 -> Alerts 1`.
- Isolated real-source Run Once against TechCrunch AI RSS with all notifiers disabled produced event-cluster diagnostics: `Fetched 5 -> Dedupe 5 -> Candidates 5 -> Events 5 -> LLM 5 -> Alerts 0`. Alerts were `0` because the temp config intentionally had no LLM API key; this verified event cluster diagnostics without sending notifications.

## Unresolved Problems / Residual Risk

- Real LLM, Gmail, Telegram, WeCom, WeChat/QQ relay, webhook credentials, and live source availability are intentionally not included. The user must configure and test real credentials locally.
- Real notification delivery was not exercised during the event-synthesis pass; isolated verification disabled all notifiers to avoid side effects.
- The in-app Browser plugin control tool was unavailable, so rendered screenshot verification was not captured. Browser UI coverage comes from `_index_html` tests and serialized runtime/status output.
- Windows packaging still requires validation on Windows or GitHub Actions.
- GitHub Actions must be run in the actual GitHub repository after upload.
- Source URLs and third-party relays can change, rate-limit, or fail independently of the app.

## Exact Next Steps

1. Review the dirty working tree and decide whether to commit the event-synthesis/readiness changes together or split them.
2. Initialize and push to a private GitHub repository:

```bash
git init
git add .
git status
git commit -m "Initial release candidate"
git branch -M main
git remote add origin <PRIVATE_REPO_URL>
git push -u origin main
```

3. Confirm CI, build, and release workflows pass in GitHub Actions.
4. Validate the Windows artifact from GitHub Actions or a Windows machine.
5. Configure real user-owned credentials locally and run E2E Test Mode plus a real Run Once with notification delivery enabled.
6. If green, tag a first release candidate such as `v0.9.0-rc1`.
