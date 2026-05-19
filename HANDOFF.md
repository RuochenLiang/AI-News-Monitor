# Handoff

## Current Goal

Finalize AI News Monitor for a first private GitHub push according to `docs/dev-history/prompts/10-clean-root-for-final-github-upload.md`: clean root directory, public upload safety, documentation polish, dependency/bootstrap checks, GitHub Actions readiness, release checklist alignment, and final handoff.

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
- Synchronized `CHATBOT_CONTEXT.md`, `HANDOFF.md`, `NEXT_VERSION_MONITORING_REPORT.md`, `docs/RELEASE_CHECKLIST.md`, docs, and changelog with the latest E2E/readiness state.
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
- `src/pipeline.py`
- `src/realtime.py`
- `src/source_reliability.py`
- `src/sources/gdelt.py`
- `tests/test_app_qt_runtime.py`
- `tests/test_e2e_operational_closure.py`
- `tests/test_release_readiness.py`
- `tests/test_sources.py`
- `CHATBOT_CONTEXT.md`
- `HANDOFF.md`
- `NEXT_VERSION_MONITORING_REPORT.md`
- `README.md`
- `README.zh-CN.md`
- `SOURCE_GUIDE.md`
- `NOTIFICATION_GUIDE.md`
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

Final local verification on 2026-05-19:

- Ruff: `python -m ruff check .` passed.
- Black check: `python -m black --check .` passed.
- Targeted source/E2E/release-readiness tests: `34 passed`, `3 skipped`.
- Full pytest: `89 passed`, `14 skipped`.
- Coverage run: `89 passed`, `14 skipped`, total coverage `54%`.
- Compileall: passed.
- `config.example.yaml` parse: passed.
- Runtime dependency check: passed.
- Workflow YAML parse: passed.
- macOS shell script syntax: passed.
- PowerShell syntax: not run locally because `pwsh` is not installed on this Mac; validate through GitHub Actions.
- Local Qt startup smoke with `QT_QPA_PLATFORM=offscreen`: passed.

## Unresolved Problems / Residual Risk

- Real LLM, Gmail, Telegram, WeCom, WeChat/QQ relay, webhook credentials, and live source availability are intentionally not included. The user must configure and test real credentials locally.
- Windows packaging still requires validation on Windows or GitHub Actions.
- GitHub Actions must be run in the actual GitHub repository after upload.
- Source URLs and third-party relays can change, rate-limit, or fail independently of the app.

## Exact Next Steps

1. Rerun the full verification commands above after final cleanup.
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
5. Configure real user-owned credentials locally and run E2E Test Mode plus a real Run Once.
6. If green, tag a first release candidate such as `v0.9.0-rc1`.
