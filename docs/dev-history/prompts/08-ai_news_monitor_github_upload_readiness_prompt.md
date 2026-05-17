# AI News Monitor — GitHub Upload Readiness Finalization Prompt

## Recommended Codex CLI command

Place this file in the repository root, then run Codex CLI from the repository root:

```text
/goal Read ./ai_news_monitor_github_upload_readiness_prompt.md carefully and implement everything described in it. Treat this file as the authoritative final pre-GitHub upload readiness specification. Before coding, read CHATBOT_CONTEXT.md, HANDOFF.md, NEXT_VERSION_MONITORING_REPORT.md, CURRENT_RUNTIME_STATUS.json, README.md, README.zh-CN.md, SOURCE_GUIDE.md, NOTIFICATION_GUIDE.md, docs/RELEASE_CHECKLIST.md, config.example.yaml, src/, tests/, locales/, and .github/workflows/. Do not assume real API keys, real Gmail credentials, real webhook tokens, or real runtime data. Do not add broad new features. Focus on release blockers, public repository readiness, E2E operational verification, documentation synchronization, dependency/bootstrap checks, and final polish. Keep source code English-only, keep Chinese only in locale/documentation resources, do not expose secrets, run tests after each milestone, and finish with a requirement-by-requirement audit.
```

---

## Current status

The latest version has implemented major capabilities:

- Local-first 24/7 monitoring
- Browser/local console
- Source reliability metadata
- Source freshness states
- Intelligence gaps
- Source cache and last-known-good fallback
- Smart polling/backoff
- Source packages
- Coverage quality
- Run Once
- E2E Test Mode
- Pipeline funnel
- `/health` and `/readiness`
- Concise browser console improvements
- Multi-channel notifications
- Fast Alert default mode
- Chinese/English i18n
- GPL-3.0-only target license
- GitHub Actions scaffolding

However, before uploading publicly to GitHub, the repository must be finalized and release blockers must be fixed.

Known blockers/risks from the latest review:

1. `LICENSE` file may be missing from the uploaded package even though GPL-3.0-only is intended.
2. `HANDOFF.md`, `CHATBOT_CONTEXT.md`, and monitoring reports may not fully describe the latest E2E closure state.
3. The full chain must be easy to verify:
   ```text
   fetch → candidate → LLM → alert → notification → UI/browser feedback
   ```
4. If no source packages are enabled, coverage becomes critical and the user must get a clear action.
5. Browser console must remain concise and must not expose raw JSON, long URLs, or code-like logs in primary cards.
6. Dependency problems such as missing `PySide6` or `feedparser` should produce clear bootstrap guidance, not confusing test failures.
7. GitHub Actions exist but need final validation/readiness checks.
8. The repository must be safe to upload publicly: no secrets, no local runtime files, no private config, no data/log artifacts.

This iteration should go **directly to a state suitable for uploading to GitHub**.

---

# Non-negotiable rules

## 1. No real secrets or private data

Do not add, assume, commit, display, or log real:

- API keys
- Gmail app passwords
- SMTP credentials
- Webhooks
- Telegram tokens
- WeCom keys
- ServerChan/Chanify/Qmsg keys
- Personal emails
- Chat IDs
- User private prompts
- Real runtime data
- Local SQLite databases
- Logs

Tests must use mocks, dummy values, fake SMTP, monkeypatching, or local fixtures.

## 2. Source code English-only

All source code must remain English-only.

Chinese is allowed only in:

- `locales/zh-CN.*`
- `README.zh-CN.md`
- Chinese documentation resources

Do not hard-code Chinese strings in Python, HTML templates, JavaScript, tests, scripts, or workflows. Use i18n keys and resource files.

## 3. Keep it lightweight

Do not introduce heavy new dependencies or broad rewrites. This is not a new feature sprint. Focus on release readiness, defects, tests, docs, and polish.

## 4. No proprietary assets

Do not bundle proprietary fonts, paid assets, or copied external project materials. Use system font stacks only.

## 5. Do not copy external project code/data

Do not copy code, feed lists, UI, documentation, assets, or data from external repositories. Only implement original code based on high-level architectural ideas already incorporated.

---

# Main objective

Make the repository safe and ready to upload as a public GitHub project.

At the end of this update, a maintainer should be able to:

1. Initialize or push the repo to GitHub.
2. Run CI successfully.
3. See clean README files in English and Chinese.
4. Confirm GPL-3.0-only license.
5. Confirm no secrets or local runtime files are present.
6. Run a local E2E Test Mode.
7. Understand source coverage/readiness.
8. Build macOS and Windows artifacts through GitHub Actions.
9. Publish a first release candidate such as `v0.9.0-rc1`.

---

# Workstream A — P0 release blocker fixes

## A1. Ensure GPL-3.0-only LICENSE exists

Add or restore a root-level file:

```text
LICENSE
```

It must contain the GPL-3.0-only license text.

Also ensure:

- `README.md` references GPL-3.0-only.
- `README.zh-CN.md` references GPL-3.0-only.
- `pyproject.toml` metadata, if present, references GPL-3.0-only consistently.
- Tests verify `LICENSE` exists.

## A2. Synchronize project state documents

Update:

- `CHATBOT_CONTEXT.md`
- `HANDOFF.md`
- `NEXT_VERSION_MONITORING_REPORT.md`
- `docs/RELEASE_CHECKLIST.md`

They must describe the latest state:

- Run Once exists.
- E2E Test Mode exists.
- Pipeline Funnel exists.
- `/readiness` exists.
- Browser console raw JSON/overflow cleanup exists.
- Source reliability/freshness/gaps exist.
- Current known limitation: real Gmail/LLM/source credentials are not included and must be tested by the user.
- Current known limitation: Windows build requires GitHub Actions or Windows runner validation.
- Current known limitation: source URLs can change and should be tested through UI.
- Current known limitation: WeChat/QQ relay stability depends on third-party relay services.

## A3. Ensure README language switching

Ensure:

- `README.md` links to `README.zh-CN.md` at the top.
- `README.zh-CN.md` links to `README.md` at the top.
- Tests cover these links.

## A4. Confirm AI disclosure

Ensure `AI_DISCLOSURE.md` exists and README files reference it.

## A5. Confirm public release docs exist

Ensure these files exist and are coherent:

- `README.md`
- `README.zh-CN.md`
- `LICENSE`
- `AI_DISCLOSURE.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `CODE_OF_CONDUCT.md` if already intended
- `SOURCE_GUIDE.md`
- `NOTIFICATION_GUIDE.md`
- `docs/INSTALL.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/RELEASE_CHECKLIST.md`
- `.env.example`
- `config.example.yaml`

---

# Workstream B — Git hygiene and public upload safety

## Objective

Prevent accidental upload of secrets, runtime state, caches, logs, data, and local build artifacts.

## Requirements

## B1. Strengthen `.gitignore`

Ensure `.gitignore` excludes:

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
*.spec
.DS_Store
```

If PyInstaller spec files are intentionally tracked, document that and adjust accordingly.

## B2. Add/verify secret scan test

Create or verify a test/script that fails if obvious secret patterns appear in tracked source/docs/examples.

Check for common patterns:

- OpenAI-style keys
- webhook tokens
- Gmail app password-like strings in code/docs
- Telegram bot token patterns
- long unredacted bearer tokens
- accidental `.env` content
- real-looking email/password combinations where inappropriate

This scan must allow safe placeholders.

## B3. Add/verify runtime artifact scan

Add a test/script or release-checklist item that confirms no runtime artifacts are included:

- local DB
- alert logs
- raw runtime logs
- cache files
- generated personal config
- built artifacts unless intentionally uploaded as release artifact

## B4. Redaction verification

Ensure logs/UI diagnostics mask:

- API keys
- app passwords
- webhook URLs
- tokens
- email password fields
- chat IDs if sensitive

Tests should cover redaction.

---

# Workstream C — E2E operational verification before release

## Objective

Make it impossible to confuse "server starts" with "full alert pipeline works".

## Requirements

## C1. E2E Test Mode must be visible and easy

Ensure the browser/local console has a clear action:

```text
E2E Test
```

or:

```text
Run E2E Test
```

It must verify, with a controlled test fixture or mock source:

```text
source fetch
→ candidate
→ LLM mock/test client
→ alert saved
→ notification attempted
→ result visible in UI
```

It must be clearly marked as test-only.

## C2. E2E result should be concise

After E2E Test, show:

```text
E2E result: success / partial / failed

Fetched: N
Candidates: N
LLM analyzed: N
Alerts saved: N
Notifications attempted: N
Notifications succeeded: N
Notifications failed: N
```

If notifications are not configured, show:

```text
Alert pipeline succeeded, but no notification channel is ready.
```

## C3. Run Once for real sources

Ensure a separate **Run Once** action exists for real sources.

Run Once should show pipeline funnel counts.

## C4. Tests

Add/verify tests for:

- E2E test mode produces a visible test alert.
- E2E test mode attempts notification through a mock notifier.
- Run Once produces a funnel summary.
- E2E test mode does not use real external credentials.
- E2E test data is clearly marked test-only.

---

# Workstream D — Pipeline funnel and zero-alert explanation

## Objective

When there are zero alerts, the user must know exactly why.

## Requirements

The dashboard/diagnostics must show a concise pipeline funnel:

```text
Fetched 441 → Language 390 → Keyword 12 → New 3 → LLM 2 → Alerts 0
```

And a concise explanation:

```text
No alerts were sent because all candidates scored below the threshold.
Top rejected candidate: score 20, threshold 80.
Recommended action: for testing, lower threshold to 50-60 or run E2E Test. For production, keep threshold high to reduce noise.
```

## Required rejection reason categories

Track:

```text
no_keyword_match
unsupported_language
duplicate
source_stale
score_below_threshold
llm_relevance_low
rate_limit
cooldown
max_alerts_per_hour
missing_notifier
notification_failed
source_package_disabled
coverage_critical
```

## Tests

Add/verify tests for:

- Zero-alert explanation.
- Below-threshold explanation.
- Top rejected candidate summary.
- Funnel counts.
- Recommended action generation.

---

# Workstream E — Browser console final cleanup

## Objective

Make the browser console suitable for daily operator use and public screenshots.

## Requirements

## E1. No raw technical overflow in primary cards

Main dashboard cards must not display:

- Full long URLs
- Raw JSON blobs
- Raw Python exception stack traces
- Full HTTP response bodies
- Full encoded GDELT queries
- Repeated unstructured log fragments

Instead, show concise summaries:

```text
GDELT: error · SSL timeout · 3 failures
Yahoo Finance RSS: rate limited · next retry in 30 min
Google News RSS: fresh · 10 articles
```

## E2. Details behind expanders

Technical details should be available behind:

```text
Show details
Copy diagnostics
```

## E3. Overflow-safe CSS

Ensure CSS handles long content:

```css
overflow-wrap: anywhere;
word-break: break-word;
max-width: 100%;
```

Long URLs should be truncated or hidden in details by default.

## E4. Event stream should be summarized

Recent events should display rows like:

```text
16:20 source_fetch · GDELT · failed
16:21 cycle_completed · 0 alerts
16:22 readiness · degraded
```

Raw JSON may exist only inside expandable details.

## E5. Tests/static checks

Add/verify tests for:

- CSS overflow-safe rules exist.
- Primary event rendering does not show raw JSON as default text.
- Diagnostics summaries are concise.
- Details still contain copyable technical data.
- Long URLs do not break main layout.

---

# Workstream F — Readiness vs health

## Objective

Make status semantics clear.

## Requirements

Keep:

```text
/health
```

as server liveness only.

Add or verify:

```text
/readiness
/api/readiness
```

Readiness should summarize:

```text
server_alive
monitor_running
llm_ready
notifier_ready
source_coverage_ready
coverage_quality
critical_gaps
last_cycle_status
can_send_alerts
```

UI must clearly distinguish:

```text
Server: alive
Monitor: running / paused / stopped
Coverage: high / medium / low / critical
Notifications: ready / degraded / not ready
LLM: ready / error / not configured
Can send alerts: yes / no
```

## Tests

Add/verify:

- `/health` liveness test.
- `/readiness` healthy test.
- `/readiness` degraded test.
- Critical coverage affects readiness.
- Missing notifier affects readiness.

---

# Workstream G — Source package and coverage guidance

## Objective

Avoid the situation where `source_packages_enabled` is empty and the user does not know what to do.

## Requirements

If no source package or custom source is enabled, show a prominent but concise warning:

```text
No source packages are enabled. Enable at least one source package or custom source.
```

If enabled packages have no fresh sources, show:

```text
Enabled packages are not fresh. Test sources, wait for backoff, or add alternative sources.
```

Source package cards should show:

- Enabled / disabled
- Number of included sources
- Fresh sources
- Failing sources
- Last package test
- Recommended use case
- Apply/enable button

## Tests

Add/verify:

- No source package warning.
- Enabled package with no fresh sources warning.
- Package source count serialization.
- Package freshness serialization.

---

# Workstream H — Source/runtime blockers

## H1. GDELT production-shaped diagnostics

Ensure GDELT diagnostics can test production-shaped topic queries, not only tiny diagnostic queries.

Handle:

- Non-JSON response
- Empty body
- 429
- Timeout
- SSL/network errors
- Query too long or malformed

Do not crash on `response.json()` if response body is not JSON.

## H2. Yahoo 429 handling

Ensure Yahoo 429 is classified as rate limit and displayed concisely:

```text
Yahoo Finance RSS: rate limited · next retry in 30 minutes
```

Do not dump raw 429 URL/errors in main console cards.

## H3. Email readiness consistency

Ensure Email health validates:

- SMTP host
- SMTP port
- encryption
- username
- password/app password
- from address
- recipients

If `from_address` is missing or invalid, health must not show ok.

If `from_address != username`, show a warning.

## Tests

Add/verify tests for:

- GDELT non-JSON.
- GDELT 429.
- GDELT timeout/SSL error.
- Yahoo 429 classification/backoff.
- Email missing from address.
- Email invalid from address.
- Email health/setup diagnostics consistency.

---

# Workstream I — Dependency/bootstrap check

## Objective

If required dependencies such as `PySide6` or `feedparser` are missing, users should see clear setup guidance.

## Requirements

Add or improve a dependency check script or startup check that reports:

- Missing required runtime dependency.
- How to install dependencies.
- Which command to run.
- Whether the app is running in a virtual environment.

Example:

```text
Missing dependency: feedparser
Run: python -m pip install -r requirements.txt
```

If PySide6 is missing and the desktop app cannot start, the user should get a clear message.

## Tests

Add/verify tests for dependency-check helper if practical.

---

# Workstream J — GitHub Actions and release artifact readiness

## Requirements

Ensure workflows exist and are coherent:

- `.github/workflows/ci.yml`
- `.github/workflows/build.yml`
- `.github/workflows/release.yml`

CI should run:

- ruff
- black
- pytest
- compileall
- config validation
- env example validation
- no secrets/source-code Chinese checks

Build should cover:

- macOS
- Windows

Release should upload zip artifacts.

Do not require real user secrets.

## Tests/static checks

Add or verify tests that workflows exist and reference expected commands.

---

# Workstream K — Documentation finalization

Update:

- `README.md`
- `README.zh-CN.md`
- `SOURCE_GUIDE.md`
- `NOTIFICATION_GUIDE.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `CHANGELOG.md`
- `HANDOFF.md`
- `CHATBOT_CONTEXT.md`
- `NEXT_VERSION_MONITORING_REPORT.md`

## Must document

- E2E Test Mode.
- Run Once.
- Pipeline Funnel.
- Why 0 alerts can happen.
- Difference between `/health` and `/readiness`.
- What coverage critical means.
- What to do when no source packages are enabled.
- GDELT/Yahoo common failures.
- Gmail From Address requirement.
- How to prepare for GitHub upload.
- What remains to validate manually after upload.

## Release checklist must include

- Run E2E Test.
- Confirm at least one alert saved.
- Confirm at least one notification attempted.
- Run Run Once.
- Confirm pipeline funnel visible.
- Confirm no raw JSON/URLs overflow browser cards.
- Confirm LICENSE exists.
- Confirm no secrets.
- Confirm GitHub Actions pass.
- Confirm Windows build artifact.

---

# Workstream L — Tests

Add or update tests for:

1. LICENSE exists and is GPL-3.0-only.
2. Handoff/context files mention E2E Test Mode and readiness.
3. E2E Test Mode visible and produces alert with mock notifier.
4. Run Once produces pipeline funnel.
5. Zero-alert explanation.
6. Browser console no raw JSON in primary event rows.
7. Browser console overflow-safe CSS.
8. Long URL diagnostics summarized.
9. `/readiness` endpoint.
10. Health vs readiness distinction.
11. Paused/running state visibility.
12. No source packages warning.
13. Enabled package no-fresh warning.
14. GDELT production-shaped diagnostics.
15. GDELT non-JSON response.
16. Yahoo 429 classification.
17. Email from address readiness.
18. Dependency check helper.
19. GitHub Actions workflow existence.
20. No Chinese in source code.
21. No obvious secrets.
22. Config example parses.
23. Existing source reliability/freshness tests still pass.
24. Existing notification/LLM diagnostics tests still pass.

---

# Final audit report

At completion, output:

```text
## Completed
- ...

## Partially completed
- ...

## Not completed / blocked
- ...

## Release blockers fixed
- ...

## E2E operational closure
- ...

## Browser console cleanup
- ...

## Readiness and coverage
- ...

## Source/runtime fixes
- GDELT:
- Yahoo:
- Email:
- Source packages:

## Dependency/bootstrap checks
- ...

## GitHub upload readiness
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

- `LICENSE` exists and GPL-3.0-only is documented.
- Handoff/context/docs are synchronized with latest E2E closure state.
- E2E Test Mode is visible and can prove alert pipeline with test data/mock notifier.
- Run Once is available for real sources.
- Pipeline Funnel explains 0-alert cycles.
- Browser console does not show raw JSON/long URL/code-like overflow in primary cards.
- `/health` and `/readiness` are clearly separated.
- No source package enabled warning is visible.
- GDELT/Yahoo known runtime failures are classified and concise.
- Email readiness validates From Address.
- Dependency check gives clear guidance for missing PySide6/feedparser.
- GitHub Actions workflows are present and coherent.
- Tests pass in a proper dependency-installed environment.
- Source code remains English-only.
- No secrets or runtime artifacts are committed.
- The repository is ready to push to GitHub as a public release candidate.
