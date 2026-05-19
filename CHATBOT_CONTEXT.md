# Chatbot Context for AI News Monitor

Generated: 2026-05-19 after final private GitHub-upload cleanup verification

## Read This First

This file is the fastest entry point for another chatbot or coding agent. It summarizes the current project state, the release-readiness work already completed, the files to inspect first, and the residual manual checks before a public GitHub release.

The project folder may not be a git repository in this local workspace. Treat these files as a public-upload candidate snapshot, then initialize or push to GitHub from a clean repository.

## Current State

AI News Monitor is a local-first desktop application with a lightweight local browser console at:

```text
http://127.0.0.1:8765
```

It monitors public Chinese and English information sources, ranks source-grounded articles against user topics, uses the user's OpenAI-compatible LLM for translation, summaries, relevance checks, and optional analysis, then sends phone-friendly alerts through configured notification channels.

The app is not a trading bot, investment adviser, broker integration, or stock recommender.

## Latest Completed Work

- Run Once exists for immediate real-source monitoring cycles.
- E2E Test Mode exists and uses a clearly marked local `[E2E TEST]` fixture plus deterministic test LLM analysis.
- Pipeline Funnel exists and records fetch, language, keyword, dedupe, ranking, LLM, alert, notification, top rejection reasons, zero-alert explanation, and recommended action.
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
- `src/monitor.py`: monitor loop, E2E Test Mode, source fetching, LLM analysis, alert saving, notification sending.
- `src/pipeline.py`: per-cycle funnel counts, rejection reasons, zero-alert explanations.
- `src/realtime.py`: browser console, `/health`, `/readiness`, `/api/control`, source diagnostics, HTML/CSS/JS.
- `src/dependency_check.py`: runtime dependency check helper.
- `src/source_reliability.py`: freshness, gaps, source packages, coverage, backoff helpers.
- `src/notifiers/`: Email, Telegram, WeCom, relay webhook, generic webhook.
- `src/sources/`: GDELT, Google News RSS, Yahoo Finance RSS, public/official/custom RSS, source library.
- `tests/`: regression, diagnostics, E2E closure, release-readiness, source reliability tests.
- `.github/workflows/`: CI, build, and release workflows for macOS and Windows.

## Latest Verification Snapshot

Latest local verification after the final private GitHub-upload cleanup:

- `python -m ruff check .`: passed.
- `python -m black --check .`: passed.
- Targeted source/E2E/release-readiness tests: 34 passed, 3 skipped.
- `python -m pytest`: 89 passed, 14 skipped.
- `python -m pytest --cov=src --cov-report=term-missing -q`: 89 passed, 14 skipped, 54% coverage.
- `python -m compileall src tests`: passed.
- `config.example.yaml` parse: passed.
- Runtime dependency check: passed.
- Workflow YAML parse: passed.
- macOS shell script syntax: passed.
- PowerShell syntax: not run locally because `pwsh` is not installed on this Mac; validate through GitHub Actions.
- Local Qt startup smoke with `QT_QPA_PLATFORM=offscreen`: passed.
- Source-code Chinese scan: passed for source/test/script/config/workflow files.
- Obvious secret scan: no real secrets found.
- Runtime/private file scan: no `.env`, `config.yaml`, logs, data, database files, root prompt scratch files, or generated zip archives are intended for public upload.

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
