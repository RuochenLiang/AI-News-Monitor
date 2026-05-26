# Chatbot Context for AI News Monitor

Generated: 2026-05-26 after event-synthesis verification and prompt 15 archival

## Read This First

This file is the fastest entry point for another chatbot or coding agent. It summarizes the current project state, the release-readiness work already completed, the files to inspect first, the current next-version prompt, and the residual manual checks before a public GitHub release.

The project folder is a git repository in this local workspace, and the working tree is intentionally dirty with event-synthesis plus earlier readiness/source changes. Review the diff before committing or pushing.

## Current State

AI News Monitor is a local-first desktop application with a lightweight local browser console at:

```text
http://127.0.0.1:8765
```

It monitors public Chinese and English information sources, ranks source-grounded articles against user topics, uses the user's OpenAI-compatible LLM for translation, summaries, relevance checks, and optional analysis, then sends phone-friendly alerts through configured notification channels.

The app is not a trading bot, investment adviser, broker integration, or stock recommender.

## Current Next-Version Prompt

Treat `docs/dev-history/prompts/15-intelligent-source-discovery-verification-social-deepseek.md` as the current authoritative next-version prompt. It requests intelligent source discovery with manual/auto/hybrid modes, source credibility and claim verification, multi-source event reports, optional X.com signal ingestion, DeepSeek provider support, generalized topics, concise browser report cards, compatibility migration, tests, and docs.

The prompt-15 foundation pass is implemented: source-mode config compatibility, source discovery/ranking, desktop source-selection preview, verification and notification gating models, event aggregation namespace, OpenAI/DeepSeek provider routing with retry backoff, disabled-by-default X.com ingestion through official recent-search API scaffolding with an in-session cost guard, desktop topic-schema editing, desktop OpenAI/DeepSeek/X configuration controls, per-topic report-style enforcement, browser confidence/status fields, contradiction surfacing, doctor checks, docs, and focused tests. Full prompt-15 completion still requires richer source-management controls beyond the new provider/social controls, broader bilingual docs, and live credential-backed validation.

## Latest Completed Work

- Run Once exists for immediate real-source monitoring cycles.
- E2E Test Mode exists and uses a clearly marked local `[E2E TEST]` fixture plus deterministic test LLM analysis.
- Pipeline Funnel exists and records fetch, language, keyword, dedupe, ranking, LLM, alert, notification, top rejection reasons, zero-alert explanation, and recommended action.
- Event clustering now groups related candidate articles before final LLM synthesis so one underlying event can produce one alert with event title, current status, timeline, source links, relation reason, uncertainty, and suggested follow-up.
- Event clustering ignores generic broad topic terms such as `AI` as the sole grouping reason, so unrelated stories from the same feed stay separate.
- Single-article alerts remain supported as single-source event clusters.
- Event timelines are generated only from source metadata and provided article text; exact source-mentioned dates can become timeline items, unknown dates remain unknown, and publication-time-derived timeline items are labeled.
- `/health` remains local server liveness only.
- `/readiness` and `/api/readiness` summarize monitor, LLM, notifier, source coverage, critical gaps, last cycle status, and `can_send_alerts`.
- Browser console primary cards are concise and overflow-safe; raw diagnostics and JSON are behind expandable details/copy controls.
- Source reliability, freshness states, source cache, last-known-good fallback, smart polling/backoff, intelligence gaps, source packages, and coverage quality are implemented.
- GDELT diagnostics test both production-shaped topic queries and a smoke query, and classify non-JSON, 429, timeout, TLS/network, long-query, and malformed-query failures.
- Yahoo Finance 429 is classified as `api_rate_limited`, enters source backoff, and is shown as a concise rate-limit status.
- Email readiness now validates SMTP host, port, username, app password, explicit From Address, and recipients. From Address mismatches show warnings.
- Dependency check helper exists; missing or broken PySide6/feedparser/httpx/etc. imports produce guidance to run `python -m pip install -r requirements.txt`.
- macOS Qt startup now copies PySide6 Qt plugins into a clean temporary cache before `QApplication` starts, which avoids plugin load failures from copied/quarantined venv files.
- `.gitignore`, tests, and docs now cover public upload safety, obvious secret scans, runtime artifact scans, workflow checks, root prompt cleanup, and GPL-3.0-only release metadata.
- Historical development prompts were moved out of the root into `docs/dev-history/prompts/`.
- Prompt archive links now point at standalone numbered files, with `docs/dev-history/prompt.md` retained as a consolidated reference.
- Prompt 15 is archived and linked as `docs/dev-history/prompts/15-intelligent-source-discovery-verification-social-deepseek.md`.
- Source discovery/ranking, verification gate, DeepSeek routing, X.com source ingestion, contradiction surfacing, doctor checks, and browser report status/confidence fields are now covered by focused tests.
- Desktop topic editing now covers prompt-15 fields such as source mode, domains, preferred regions, social enablement, confidence threshold, and report-style flags.
- Desktop topic preview now shows manual and auto-selected sources with reason, expected value, risk, and priority before a monitor cycle runs.
- Desktop settings now cover OpenAI/DeepSeek primary/fallback routing, local provider keys, DeepSeek retry fields, and X.com recent-search/cost-guard settings.
- Per-topic report-style flags now shape LLM prompt preferences and final alerts for timeline, source comparison, and suggested-action sections.
- X.com is only selected for eligible auto/hybrid social topics and enforces its configured in-session daily read-post guard.
- OpenAI-compatible LLM calls honor configured retry backoff before provider fallback.
- GDELT multi-keyword OR queries are wrapped in parentheses for safer production query syntax.
- E2E Test Mode can be rerun without stored-alert dedupe blocking the controlled second test alert.
- `CURRENT_RUNTIME_STATUS.json` was treated as local runtime data and removed from the public-upload candidate.

## How To Run Locally

On macOS:

```bash
cd "/path/to/AI-News-Monitor"
./scripts/run_macos.sh
```

Then open:

```text
http://127.0.0.1:8765
```

Useful endpoints:

```text
http://127.0.0.1:8765/health
http://127.0.0.1:8765/readiness
http://127.0.0.1:8765/status
http://127.0.0.1:8765/events
```

Use the desktop app for credentials and setup. Use the browser console for live monitoring, Run Once, E2E Test Mode, readiness, source health, notification health, pipeline funnel, recent alerts, and concise events.

## Important Files

- `HANDOFF.md`: latest implementation handoff and verification notes.
- `docs/dev-history/prompts/`: historical development prompts and readiness specifications. These are retained for context only and are not required for normal use.
- `README.md` and `README.zh-CN.md`: user-facing docs with language links, GPL-3.0-only, AI disclosure, run instructions, readiness, Run Once, E2E Test Mode, Pipeline Funnel, and troubleshooting.
- `SOURCE_GUIDE.md`: public-source policy, source packages, source freshness, GDELT/Yahoo failure guidance.
- `NOTIFICATION_GUIDE.md`: notification setup, Gmail From Address requirement, diagnostics, fallback routing.
- `docs/RELEASE_CHECKLIST.md`: public release checklist.
- `docs/ARCHITECTURE.md`, `docs/INSTALL.md`, `docs/ROADMAP.md`: architecture, install, and future work.
- `src/monitor.py`: monitor loop, E2E Test Mode, source fetching, event clustering, LLM event analysis, alert saving, notification sending.
- `src/event_clustering.py` and `src/event_synthesis.py`: deterministic event grouping, source-link payloads, timeline extraction, and event status serialization.
- `src/pipeline.py`: per-cycle funnel counts, event cluster diagnostics, rejection reasons, zero-alert explanations.
- `src/realtime.py`: browser console, `/health`, `/readiness`, `/api/control`, source diagnostics, HTML/CSS/JS.
- `src/dependency_check.py`: runtime dependency check helper.
- `src/source_reliability.py`: freshness, gaps, source packages, coverage, backoff helpers.
- `src/notifiers/`: Email, Telegram, WeCom, relay webhook, generic webhook.
- `src/sources/`: GDELT, Google News RSS, Yahoo Finance RSS, public/official/custom RSS, source library.
- `tests/`: regression, diagnostics, E2E closure, release-readiness, source reliability tests.
- `.github/workflows/`: CI, build, and release workflows for macOS and Windows.

## Latest Verification Snapshot

Latest local verification after the prompt 15 foundation pass:

- `python -m ruff check .`: passed.
- `python -m black --check .`: passed; `102 files would be left unchanged`.
- `python -m pytest -q`: `140 passed`, `14 skipped`.
- `python -m compileall ai_news_monitor src tests`: passed.
- `python -c "from pathlib import Path; from src.config import load_config; load_config(Path('config.example.yaml'), load_env=False); print('config ok')"`: `config ok`.
- `git diff --check`: passed.
- `python -m ai_news_monitor doctor --check-llm --config config.example.yaml --json`: command path works and reports the expected missing placeholder API key.
- Isolated E2E Test Mode with all notifiers disabled produced one event-level alert: `Fetched 1 -> Dedupe 1 -> Candidates 1 -> Events 1 -> LLM 1 -> Alerts 1`.
- Isolated real-source Run Once against TechCrunch AI RSS with all notifiers disabled produced event-cluster diagnostics: `Fetched 5 -> Dedupe 5 -> Candidates 5 -> Events 5 -> LLM 5 -> Alerts 0`. Alerts were `0` because no LLM API key was provided in the isolated temp runtime.

Run the full checks again after any additional edits:

```bash
source .venv/bin/activate
python -m ruff check .
python -m black --check .
python -m pytest -q
python -m pytest --cov=src --cov-report=term-missing -q
python -m compileall src tests
```

## Known Residual Risk

- Real LLM API keys, Gmail accounts, SMTP provider policy, webhook tokens, chat IDs, and live public feed availability are not bundled or assumed. The user must configure and test them locally in the desktop app.
- Real notification delivery was not exercised during the event-synthesis pass; isolated verification disabled all notifiers to avoid side effects.
- The in-app Browser plugin control tool was unavailable, so rendered screenshot verification was not captured. Browser UI coverage comes from `_index_html` tests and serialized runtime/status output.
- Windows packaging was not built locally on this Mac. Validate on a Windows runner or GitHub Actions before publishing Windows artifacts.
- GitHub Actions files are present and checked statically, but they must pass in the actual GitHub repository after upload.
- Public source URLs can change or rate-limit. Users should test sources through the desktop app and monitor source readiness.
- WeChat/QQ relay stability depends on third-party relay services.
- Remote authenticated console mode is not implemented; local server defaults to `127.0.0.1`.

## Suggested Next Questions For A Chatbot

- Review `docs/RELEASE_CHECKLIST.md` before creating a public release.
- Verify GitHub Actions after pushing to a private repository.
- Validate Windows packaging on GitHub Actions or a Windows machine.
- Run E2E Test Mode locally with a configured or mocked notification channel.
- Prepare a first release candidate tag such as `v0.9.0-rc1` after CI passes.

## Private GitHub Push Commands

```bash
git init
git add .
git status
git commit -m "Initial release candidate"
git branch -M main
git remote add origin <PRIVATE_REPO_URL>
git push -u origin main
```
