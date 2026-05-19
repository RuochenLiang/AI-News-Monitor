# AI News Monitor — Final GitHub Upload Cleanup Prompt

## Recommended Codex CLI command

From the repository root, run Codex CLI with this archived prompt:

```text
/goal Read ./docs/dev-history/prompts/10-clean-root-for-final-github-upload.md carefully and implement everything described in it. Treat this file as the authoritative final GitHub-upload cleanup specification. Before coding, read CHATBOT_CONTEXT.md, HANDOFF.md, NEXT_VERSION_MONITORING_REPORT.md, README.md, README.zh-CN.md, SOURCE_GUIDE.md, NOTIFICATION_GUIDE.md, docs/RELEASE_CHECKLIST.md, config.example.yaml, src/, tests/, locales/, .github/workflows/, .gitignore, pyproject.toml, requirements.txt, and requirements-dev.txt. Do not assume real API keys, real Gmail credentials, real webhook tokens, real notification targets, or real runtime data. Do not push to GitHub or create a remote. Focus only on making the local repository clean, safe, professional, and ready for a first private GitHub push. Keep source code English-only, keep Chinese only in locale/documentation resources, avoid broad feature changes, run tests/checks after each milestone, and finish with a GitHub-upload readiness audit plus exact next commands for the user.
```

---

## Purpose

The project is now close to a public GitHub release candidate. This iteration is not a feature sprint. It is a **final repository cleanup and GitHub-upload preparation pass**.

The goal is to make the repo look professional, safe, coherent, and ready to push first to a private GitHub repository for CI/build validation.

Do not add large new features. Do not rewrite architecture. Do not change product behavior unless needed to pass readiness checks.

---

# Non-negotiable rules

## 1. Do not use real secrets or runtime data

Do not add, assume, commit, display, or log real:

- LLM API keys
- Gmail app passwords
- SMTP credentials
- Email addresses
- Telegram tokens
- WeCom webhook URLs
- WeChat/QQ relay keys
- Generic webhook URLs
- User private prompts
- Real runtime alerts
- SQLite runtime databases
- Logs
- Cache files

## 2. Source code must remain English-only

All source code must remain English-only.

Chinese text is allowed only in:

- `locales/zh-CN.*`
- `README.zh-CN.md`
- Chinese documentation resources

Do not hard-code Chinese strings in source code, tests, scripts, HTML templates, CSS, JS, or workflows.

## 3. Keep repository lightweight

Do not introduce heavy new dependencies.
Do not add generated artifacts to the repository unless they are meant to be source-controlled.
Do not commit build outputs.

## 4. Do not push to GitHub

Do not run `git push`.
Do not create a remote.
Do not publish a release.

Prepare the local repo and provide exact next commands for the user.

---

# Workstream A — Clean root directory

## Objective

The root directory should look like a professional open-source project, not a development scratchpad.

## Current concern

There may be many historical prompt files in the root, such as:

```text
07-add-source-reliability-freshness-and-intelligence-gaps.md
08-finalize-github-upload-readiness-and-release-gates.md
04-improve-fast-alerts-ui-i18n-sources-notifications.md
11-verify-next-phase-features-and-runtime-stability.md
06-stabilize-llm-email-source-diagnostics-and-setup-ux.md
02-expand-into-24-7-global-information-agent.md
05-prepare-v0-9-open-source-release-candidate.md
09-prove-e2e-alert-delivery-and-clean-browser-console.md
01-build-lightweight-desktop-ai-news-monitor.md
03-add-presets-minimal-ui-and-source-management.md
```

These files are useful development history but should not clutter the root of a public repository.

## Requirements

1. Identify all root-level development prompt files.
2. Move them out of the root into:

```text
docs/dev-history/prompts/
```

3. Add a short file:

```text
docs/dev-history/README.md
```

explaining that these prompts are historical development notes and not required for normal use.

4. Do not delete files unless they are obvious duplicates or generated temporary artifacts. Prefer moving over deleting.

5. Ensure README/quick start does not reference those prompt files as required files.

6. Keep the root focused on:

```text
README.md
README.zh-CN.md
LICENSE
AI_DISCLOSURE.md
CONTRIBUTING.md
SECURITY.md
CHANGELOG.md
CODE_OF_CONDUCT.md
SOURCE_GUIDE.md
NOTIFICATION_GUIDE.md
config.example.yaml
.env.example
pyproject.toml
requirements.txt
requirements-dev.txt
main.py
src/
tests/
docs/
locales/
scripts/
.github/
```

## Tests/checks

Add or update a release-readiness test/check that warns if unexpected prompt/spec scratch files remain in the root.

---

# Workstream B — Public repository safety scan

## Objective

Ensure nothing unsafe or private will be uploaded.

## Requirements

Verify or improve checks for:

- `.env` not present/tracked.
- `config.yaml` not present/tracked.
- `data/` not present/tracked.
- `logs/` not present/tracked.
- `*.sqlite`, `*.db`, `*.log` not present/tracked.
- No obvious API key patterns.
- No unredacted webhook URLs.
- No Gmail app-password-like strings.
- No Telegram token patterns.
- No real-looking secrets in docs/examples.
- No local runtime status JSON.
- No build artifacts in the repo root unless intentionally ignored.

## `.gitignore`

Ensure `.gitignore` excludes at least:

```text
.env
.env.*
!.env.example
config.yaml
data/
logs/
*.sqlite
*.db
*.log
.cache/
.pytest_cache/
.mypy_cache/
.ruff_cache/
__pycache__/
dist/
build/
.DS_Store
```

If any files under these patterns are needed, explain why.

## Tests/checks

Run existing release readiness tests and add missing ones if necessary.

---

# Workstream C — Documentation final polish

## Objective

Make documentation coherent for a first-time GitHub visitor.

## Requirements

Review and polish:

- `README.md`
- `README.zh-CN.md`
- `SOURCE_GUIDE.md`
- `NOTIFICATION_GUIDE.md`
- `docs/INSTALL.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/RELEASE_CHECKLIST.md`
- `AI_DISCLOSURE.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CHANGELOG.md`

## Must verify

1. `README.md` links to `README.zh-CN.md`.
2. `README.zh-CN.md` links to `README.md`.
3. Both README files explain:
   - What the project is.
   - What it is not.
   - Quick start.
   - First-run setup.
   - LLM setup.
   - Gmail/email setup.
   - Notification setup.
   - Source setup.
   - Local console.
   - E2E Test Mode.
   - Run Once.
   - Pipeline Funnel.
   - `/health` vs `/readiness`.
   - Tests.
   - Packaging.
   - Troubleshooting.
   - Financial-advice disclaimer.
   - No paywall/login bypass disclaimer.
   - AI-assisted development disclosure.
   - GPL-3.0-only license.
4. Docs do not claim that real personal WeChat/QQ native bot APIs are stable. They should describe relay services honestly.
5. Docs do not claim Windows build has been locally verified if it has not.
6. Docs explain that GitHub Actions should be run after first private push.

## Changelog

Update `CHANGELOG.md` with a clear unreleased or `v0.9.0-rc1` section summarizing:

- E2E Test Mode
- Run Once
- Pipeline Funnel
- Readiness endpoint
- Source reliability/freshness/gaps
- Browser console cleanup
- Interface diagnostics
- GitHub upload readiness

---

# Workstream D — License and open-source metadata

## Objective

Ensure open-source release metadata is correct.

## Requirements

1. Ensure root-level `LICENSE` exists and contains GPL-3.0-only text.
2. Ensure `pyproject.toml` uses GPL-3.0-only consistently.
3. Ensure both README files reference GPL-3.0-only.
4. Ensure `AI_DISCLOSURE.md` exists and is referenced.
5. Ensure no incompatible copied code/assets are introduced.
6. Ensure no proprietary font files are included.
7. Ensure no external project code/data was copied.

## Tests/checks

Run or add tests for:

- License exists.
- License contains GPL v3 wording.
- README references license.
- AI disclosure exists.
- No font files are unexpectedly committed.

---

# Workstream E — GitHub Actions readiness

## Objective

Prepare GitHub Actions for first private push.

## Requirements

Verify workflows exist:

```text
.github/workflows/ci.yml
.github/workflows/build.yml
.github/workflows/release.yml
```

## CI should cover

- Install dependencies.
- `ruff`
- `black --check`
- `pytest`
- `python -m compileall src tests`
- `config.example.yaml` validation.
- `.env.example` validation.
- no secrets check.
- no source-code Chinese check.
- release readiness tests.

## Build should cover

- macOS artifact.
- Windows artifact.
- Upload artifacts.
- No real user secrets required.

## Release should cover

- Tag-triggered release.
- Build artifacts attached.
- No real user secrets required except `GITHUB_TOKEN`.

## Requirements

1. Do not run remote GitHub Actions locally.
2. Validate workflow YAML syntax if practical.
3. Ensure workflows do not reference missing files/scripts.
4. Ensure workflows are documented in README or docs.

## Final output must include

Exact commands for the user:

```bash
git init
git add .
git status
git commit -m "Initial release candidate"
git branch -M main
git remote add origin <PRIVATE_REPO_URL>
git push -u origin main
```

Also recommend pushing to a private repo first and checking Actions before making public.

---

# Workstream F — Dependency/bootstrap check

## Objective

Prevent confusion when dependencies are missing.

## Requirements

Ensure a dependency check exists or add one that reports missing:

- PySide6
- feedparser
- httpx
- beautifulsoup4
- PyYAML
- python-dotenv

It should show a clear command:

```bash
python -m pip install -r requirements.txt
```

If dev dependencies are needed:

```bash
python -m pip install -r requirements-dev.txt
```

## Tests

Add/update tests for dependency check helper using monkeypatching.

---

# Workstream G — E2E and release checklist verification

## Objective

Ensure release checklist matches actual product capabilities.

## Requirements

Update `docs/RELEASE_CHECKLIST.md` so it includes:

1. Install dependencies.
2. Run dependency check.
3. Launch app.
4. Open local console.
5. Configure LLM with real user key.
6. Test LLM.
7. Configure Gmail with app password.
8. Test Email.
9. Configure at least one fallback notifier.
10. Run E2E Test Mode.
11. Confirm at least one test alert saved.
12. Confirm notification attempted/succeeded or documented as not configured.
13. Run Run Once.
14. Confirm Pipeline Funnel visible.
15. Confirm `/health`.
16. Confirm `/readiness`.
17. Confirm no raw JSON/URL overflow in browser cards.
18. Enable source packages.
19. Test enabled sources.
20. Create production topic.
21. Start monitoring.
22. Confirm logs do not reveal secrets.
23. Run tests.
24. Confirm GitHub Actions pass after private push.
25. Confirm Windows artifact from Actions.
26. Make repo public only after CI/build pass.

## Tests

Ensure checklist exists and contains key terms:

- E2E Test
- Run Once
- Pipeline Funnel
- readiness
- Gmail App Password
- GitHub Actions
- private repo

---

# Workstream H — Final local tests and checks

## Required checks

Run, if available in the environment:

```bash
python -m pytest -q
python -m compileall src tests
python -m ruff check .
python -m black --check .
```

If dependencies are missing, do not pretend tests passed. Instead:

1. Run the dependency check.
2. Report missing dependencies.
3. Provide exact install command.
4. Run whatever tests can run.
5. Explain blocked tests honestly.

## Targeted tests

At minimum, ensure these targeted tests pass if dependencies are installed:

- release readiness tests
- E2E operational closure tests
- source reliability/freshness tests
- notification/LLM diagnostics tests
- source-code English-only / no Chinese scan
- config parse test

---

# Workstream I — Final handoff

## Objective

Produce a clear final handoff for the user.

Update `HANDOFF.md` and `CHATBOT_CONTEXT.md` with:

- Current version status.
- What is ready.
- What still requires user verification.
- What GitHub upload steps remain.
- Exact commands to initialize and push to a private repo.
- Known limitations:
  - Real LLM/Gmail/webhook credentials must be tested by user.
  - Windows artifact must be verified through Actions.
  - Source URLs can change.
  - WeChat/QQ relay depends on third-party services.
  - Public source rate limits may occur.
- Recommended first release tag:
  ```text
  v0.9.0-rc1
  ```

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

## Repository cleanup
- ...

## Public upload safety
- ...

## Documentation
- ...

## License and metadata
- ...

## GitHub Actions readiness
- ...

## Dependency/bootstrap checks
- ...

## E2E/release checklist
- ...

## Tests run
- ...

## Files moved/removed
- ...

## Remaining risks
- ...

## Exact next commands for user
- ...
```

---

# Definition of done

This iteration is complete only when:

- Root directory is clean and professional.
- Historical prompt/spec scratch files are moved out of root or intentionally documented.
- LICENSE exists and GPL-3.0-only is consistently documented.
- README English/Chinese links work.
- Public release docs are coherent.
- `.gitignore` protects secrets/runtime files.
- Secret/runtime artifact scans pass.
- GitHub Actions workflows are present and coherent.
- Dependency check provides clear guidance.
- Release checklist is actionable.
- HANDOFF and CHATBOT_CONTEXT reflect the latest state.
- Tests/checks are run or honestly reported as blocked by missing dependencies.
- The user receives exact commands to push first to a private GitHub repository.
- No secrets or local runtime data are included.

---
