# AI News Monitor v0.9 — Final Target Candidate + Open Source Release Readiness

## Recommended Codex CLI command

Place this file in the repository root, then run Codex CLI from the repository root and use:

```text
/goal Read ./docs/dev-history/prompts/05-prepare-v0-9-open-source-release-candidate.md carefully and implement everything described in it. Treat this file as the authoritative product and engineering specification for the next major iteration. Before coding, read HANDOFF.md, README.md, SOURCE_GUIDE.md, NOTIFICATION_GUIDE.md, config.example.yaml, src/, and tests/. Do not assume real API keys or real run data. Work in milestones, run tests after each milestone, avoid hard-coded secrets, keep all source code English-only, prepare the repository for public open-source release under GPL-3.0-only, and finish with a requirement-by-requirement audit.
```

---

## Mission

Build the next major iteration of AI News Monitor as:

> A local-first, 24/7, high-quality Chinese/English information radar that runs on the user's computer as a temporary local server, monitors enough public Chinese and English information sources worldwide, finds information close to the user's prompts/keywords, and delivers timely source-grounded alerts to phone-friendly channels such as email and messaging apps.

This project is **not** a trading bot, stock recommender, or investment advisor.
Its primary job is **timely high-quality information delivery**, not deep automated decision-making.

The user performs deeper analysis manually.

---

# Non-negotiable hard requirements

## 1. Source code must contain no Chinese text

All source code must be English-only.

This applies to:

- Python identifiers
- Python comments
- Python docstrings
- Log message templates in code
- Error message templates in code
- UI strings embedded directly in source files
- HTML templates embedded directly in source files
- QSS/CSS comments
- JavaScript/TypeScript code if any
- Test names and test comments
- Script names and script comments
- GitHub Actions workflow comments

### Allowed exceptions

Chinese text may exist only in clearly separated user-facing resource/documentation files, such as:

- `locales/zh-CN.json`
- `locales/zh-CN.yaml`
- `README.zh-CN.md`
- Chinese user documentation under `docs/zh-CN/`
- Example Chinese user prompts in documentation only

Do **not** hard-code Chinese UI strings in Python/PySide code.
Do **not** hard-code Chinese notification strings in notifier classes.
Do **not** hard-code Chinese browser dashboard strings in Python HTML templates.

Use i18n keys and separate locale resource files.

Example:

```python
# Good
title = i18n.t("settings.llm.title")

# Bad
title = "语言设置"
```

## 2. README must support English/Chinese switching

The public GitHub repository must include:

- `README.md` — English main README
- `README.zh-CN.md` — Simplified Chinese README

Each README must link to the other at the top:

In `README.md`:

```markdown
[简体中文](README.zh-CN.md)
```

In `README.zh-CN.md`:

```markdown
[English](README.md)
```

The English README should be the default GitHub README.
The Chinese README should be fully readable for non-expert Chinese users.

## 3. GPL license

Use:

```text
GPL-3.0-only
```

Add a `LICENSE` file containing the GPL-3.0-only license text.
Reference GPL-3.0-only in both README files.

## 4. AI-assisted development disclosure

Add an AI-assisted development disclosure, but phrase it as human-reviewed and maintained.

Add `AI_DISCLOSURE.md` and reference it from both README files.

Recommended wording:

```text
This project was developed with AI assistance. AI-assisted code, documentation, and tests should be reviewed, tested, and maintained by the project owner or contributors before release.
```

Chinese wording may appear only in `README.zh-CN.md` or `docs/zh-CN/`, not in source code.

## 5. No hard-coded secrets

Never hard-code:

- LLM API keys
- SMTP usernames/passwords
- Email app passwords
- Webhook URLs
- Telegram tokens
- WeCom webhook keys
- ServerChan/Chanify/Qmsg keys
- Generic webhook secrets
- User private prompts
- Real personal email addresses
- Real chat IDs

Use `.env`, local config, or secure local settings.

Ensure `.gitignore` excludes:

```text
.env
config.yaml
data/
logs/
*.sqlite
*.db
*.log
```

---

# Product target

This version should become a **Final Target Candidate**, meaning it should be close to what the user ultimately wants:

- A local app/server running on the user's laptop/desktop
- A modern local control console
- High-quality Chinese/English source monitoring
- Fast source-first alerting
- Stable notification delivery
- Easy setup
- Easy debugging
- Clean open-source repository
- Bilingual documentation
- Strong tests and GitHub Actions
- No real secrets or private user data in the repository

---

# Read first

Before implementing, read these files in order:

1. `HANDOFF.md`
2. `README.md`
3. `SOURCE_GUIDE.md`
4. `NOTIFICATION_GUIDE.md`
5. `config.example.yaml`
6. `src/`
7. `tests/`

Do not assume real API keys, real notification credentials, or real runtime data.

Then produce a concise implementation plan with milestones.

---

# Product principles

## Timeliness first

The highest-value feature is 24/7 near-real-time discovery and delivery.

Do not delay alerts with excessive AI analysis.
Prefer fast, concise, source-grounded alerts.

## High-quality information, not AI over-analysis

The system should deliver high-quality original information to the user.
The user will decide what it means.

LLM output should be used mainly for:

- Translation
- Short summary
- Relevance confirmation
- Match explanation
- Optional extended analysis only when enabled

## Chinese and English only

The system must support:

- Chinese prompts
- English prompts
- Chinese news sources
- English news sources
- Chinese output
- English output

Do not process other languages by default.

## Local-first server model

Default use case:

1. User launches app on their computer.
2. Local server starts.
3. User opens a local control console.
4. User configures API keys, sources, topics, and notifications.
5. App runs 24/7 and pushes alerts to phone-friendly channels.

Default local UI URL:

```text
http://127.0.0.1:<port>
```

LAN/remote access should be optional and documented carefully.

---

# Major workstreams

## Workstream A — Local browser control console as primary operator UI

### Goal

Upgrade the local browser dashboard into the main operator console, while keeping the desktop/PySide app as a launcher/tray/controller if useful.

### Requirements

Create or upgrade a lightweight local web console at `http://127.0.0.1:<port>`.

It should include:

- Dashboard
- Sources
- Notifications
- Topics
- Alerts
- Diagnostics
- Settings
- Logs

The console should show:

- Monitor running/paused/stopped
- Current local server URL/port
- Last fetch time
- Total processed articles
- Matched articles
- Alerts sent
- Queue length
- Source health
- Notification health
- LLM health
- Recent matches
- Recent alerts
- Recent errors
- SSE/WebSocket connection status
- Current language
- Current alert mode
- Current source packages enabled

### UI style

The UI must be:

- Apple-inspired
- Low-glare
- Lightweight
- Modern
- Modular
- Flat
- Calm but not boring
- Clear and fast to operate

Use:

- Soft background instead of harsh pure white
- Modular cards
- Large readable headings
- Strong typography hierarchy
- Clear spacing
- Subtle shadows or borders
- Single restrained accent colour
- Gentle transitions
- Modern dialogs/toasts
- No heavy UI dependencies unless necessary

Do not introduce a large frontend framework unless it is clearly justified.
If a web UI is built, prefer lightweight HTML/CSS/JS or another minimal approach.

### Acceptance criteria

- The browser console is useful enough to operate the local server.
- UI is visually improved compared with the current form-heavy interface.
- Dashboard, source health, notification health, alerts, and logs are visible.
- SSE or WebSocket updates appear without manual refresh.
- UI remains lightweight and responsive.

---

## Workstream B — First-run setup wizard

### Goal

Make initial setup simple for non-expert users.

### Requirements

Add a first-run setup flow if required config is missing.

Suggested steps:

1. Choose language
2. Configure LLM provider/API key/model
3. Configure at least one notification channel
4. Test notification
5. Choose source packages
6. Create first topic/prompt
7. Start monitoring

Every required user-provided value must have:

- Short explanation
- Helper link
- Test/verify button where feasible
- Clear error message
- Advanced options hidden by default

### Required helper links

Provide helper links or buttons for:

#### LLM

- OpenAI API keys page
- OpenAI-compatible base URL explanation
- Model name explanation
- Test LLM connection

#### Email

- Gmail App Password help
- Outlook/SMTP help if implemented
- SMTP host/port explanation
- Test email

#### Telegram

- BotFather link/instructions
- Chat ID instructions
- Test Telegram

#### WeCom

- WeCom group bot webhook setup guide
- Test WeCom

#### WeChat relay

- ServerChan/Server酱 guide
- Chanify guide if supported
- Explain direct personal WeChat bot APIs are not officially reliable
- Test WeChat relay

#### QQ relay

- Qmsg or supported relay guide
- Explain relay limitations
- Test QQ relay

#### Sources

- What RSS/Atom is
- How to find RSS feeds
- Source website link
- Feed test
- Examples
- Public-source limitations

### Acceptance criteria

- New user can configure the app without editing YAML manually.
- Missing required settings are obvious.
- All user-provided credential/source fields have helper links.
- Users can test connections.

---

## Workstream C — Fast Alert as default, Full Analysis optional

### Goal

Keep default alerts fast, concise, source-first, and mobile-friendly.

### Requirements

Default:

```yaml
alerts:
  default_mode: "fast"
```

Fast Alert must include:

- Title
- Translated title if needed
- Source
- Published time
- Original link
- Short summary
- Why it matched
- Matched keywords/entities
- Source reliability/context
- Multi-source confirmation/cluster context if available
- Quality score/relevance score

Fast Alert must not include by default:

- Long market analysis
- Bullish/bearish paths
- Risk essay
- Stock recommendation
- Investment advice

Full Analysis Mode can include optional extended fields:

- Why it matters
- Market relevance
- Bullish/bearish paths
- Risks
- Uncertainty notes
- Watchlist/stock candidates

Always include a disclaimer that this is not financial advice if market-related fields are shown.

### Acceptance criteria

- Fast Alert is default.
- Full Analysis Mode is opt-in.
- Tests verify Fast Alert omits deep analysis fields.
- Alerts are readable on phone screens.
- Alerts always include original source links.

---

## Workstream D — Source Library as a core product module

### Goal

Make source coverage broad, editable, testable, and high-quality.

### Current source types

Existing source types may include:

- GDELT
- Google News RSS
- Yahoo Finance RSS
- Public RSS
- Official RSS
- Source Library RSS
- Custom RSS

Preserve these, but improve source management and quality.

### Requirements

Create a modern Source Library page with categories:

- Global News
- Finance
- Official / Government
- China
- Taiwan
- US
- Semiconductor / AI
- Company IR
- Custom

Each source card should show:

- Source name
- Language: Chinese or English
- Source type: RSS, API, official press release, company IR, custom
- Category
- Reliability score
- Ownership/publisher
- Bias/context hint
- Enabled/disabled toggle
- Last fetch time
- Last success/failure state
- Consecutive failure count
- Failure reason
- Recent article count
- Test source button
- Open website button
- Help/info button

### Source wizard

Add or improve a source wizard:

1. Choose source type
2. Enter URL
3. Test URL
4. Auto-detect name/language/feed sample where feasible
5. Confirm category/reliability/metadata
6. Save source

### Source packages

Add source packages that can be enabled with one click:

- Global News Starter
- Finance Starter
- Official/Government Starter
- China/Taiwan Starter
- US Policy Starter
- Semiconductor/AI Starter
- Company IR Starter

Do not enable everything by default.
Default enabled sources should be few but high-quality.

### Curated source library target

Include at least 50 curated optional source candidates if feasible.
Do not blindly add invalid URLs. Verify public RSS/Atom/API availability where possible. If a source has no feed, keep it disabled or document it as a manual/website candidate.

Suggested categories:

#### Global / English

- GDELT
- Google News RSS
- Yahoo Finance RSS
- BBC public RSS if available
- The Guardian public RSS if available
- AP public feed if available
- Reuters only if legally/publicly available
- CNBC public RSS if available
- MarketWatch public RSS if available
- TechCrunch
- The Verge
- Ars Technica

#### Official / Government

- White House
- US Department of Commerce
- US Department of State
- US Treasury
- SEC
- USTR
- Federal Reserve
- Taiwan Presidential Office
- Taiwan Ministry of Economic Affairs
- Taiwan Financial Supervisory Commission
- Taiwan MOFA
- China State Council / 中国政府网 as a documented public source if accessible
- China Ministry of Commerce / 商务部 as a documented public source if accessible

#### Taiwan / Chinese

- Central News Agency / CNA
- Taiwan Economic Daily if public feed exists
- Commercial Times if public feed exists
- Other reputable public Chinese/Taiwan feeds if available

#### Semiconductor / AI / Company IR

- TSMC Newsroom
- NVIDIA Newsroom/blog
- ASML News
- Applied Materials News
- AMD Newsroom
- Intel Newsroom
- Broadcom News
- OpenAI News
- Google AI Blog
- Microsoft AI Blog
- Meta AI Blog
- Anthropic News
- Semiconductor Engineering
- SEMI News
- arXiv cs.AI
- TechCrunch AI
- MIT Technology Review AI
- VentureBeat AI

### Rules

- Do not scrape paywalled content.
- Do not simulate login.
- Do not bypass access controls.
- Do not use private/unlicensed data sources.
- Only use public RSS/Atom feeds, public APIs, official press pages, and public company IR/newsroom pages.

### Acceptance criteria

- User can enable/disable sources.
- User can add/test/remove custom sources.
- Source cards show status.
- Source settings persist.
- Source library is meaningfully larger than current MVP.
- Tests cover source config, source health, and custom source validation.

---

## Workstream E — Improved information quality scoring

### Goal

Improve delivered information quality without relying too heavily on LLMs.

### Requirements

Enhance scoring with:

- Keyword/prompt match strength
- Recency
- Source reliability
- Official source boost
- Company IR/newsroom boost
- Multi-source confirmation boost
- Source category priority
- User whitelist
- User blacklist
- Duplicate/rewritten-source penalty
- Low-quality aggregator penalty
- Language match/preference
- Original source link presence
- Event cluster strength

Add or preserve config:

```yaml
quality:
  official_source_boost: 0.10
  company_ir_boost: 0.10
  multi_source_confirmation_boost: 0.15
  low_quality_source_penalty: 0.20
  whitelist_boost: 0.20
  blacklist_exclude: true
```

Every selected alert should include a short explainable reason:

```text
Selected because:
- Matched 5 terms
- Source reliability: 0.92
- Published 8 minutes ago
- Confirmed by 3 sources
- Official source boost applied
```

### Acceptance criteria

- Quality scoring is explainable.
- Multi-source confirmation increases score.
- Blacklist/whitelist works.
- Official/company sources rank higher.
- Low-quality aggregators rank lower.
- Tests cover behavior.

---

## Workstream F — Notification Center reliability

### Goal

Make notification delivery stable for long-running use.

### Requirements

Create a Notification Center page with channel cards:

- Email
- Telegram
- WeCom
- WeChat Relay
- QQ Relay
- Generic Webhook

Each card should show:

- Configured/unconfigured
- Enabled/disabled
- Connected/failed
- Last success time
- Last failure time
- Failure count
- Last error
- Retry state
- Fallback priority
- Test button
- Setup guide/helper link

### Retry and fallback

Implement or improve:

```yaml
notifications:
  fallback_enabled: true
  retry_attempts: 2
  retry_base_delay_seconds: 0.5
  fallback_order:
    - email
    - telegram
    - wecom
    - wechat_relay
    - qq_relay
    - generic_webhook
```

Behavior:

1. Try primary enabled channel.
2. If it fails, retry with exponential backoff.
3. If still failing, try fallback channels in order.
4. Record delivery result.
5. Show result in UI and logs.

### WeChat/QQ reality

Do not promise stable native personal WeChat/QQ bot APIs.

Use:

- WeChat Relay
- QQ Relay
- Generic Webhook Relay

Document that reliability depends on the third-party relay provider. Recommend configuring Email or Telegram as backup.

### Acceptance criteria

- Notifier health is visible.
- Test notification works for configured channels.
- Fallback routing is tested.
- Retry/backoff is tested.
- Errors are clear and actionable.

---

## Workstream G — Complete Chinese/English i18n through resource files

### Goal

When language is selected, the entire user-facing app output uses that language consistently.

### Requirements

Supported languages:

- `zh-CN`
- `en`

All user-facing text must be resolved from resource files or i18n keys.

This includes:

- Desktop UI
- Browser console
- Notifications
- Logs shown to users
- Dialogs/toasts
- Error messages
- Helper text
- Settings labels
- Source manager
- Notification manager
- First-run wizard
- Alert formatting
- Local server dashboard

### Source code English-only rule

Do not put Chinese strings in source code.
Chinese strings must live in `locales/zh-CN.*` or Chinese docs only.

### README language switch

Implement:

- `README.md` English
- `README.zh-CN.md` Simplified Chinese
- Cross-links at top

### Acceptance criteria

- UI language switch changes all pages.
- No obvious hard-coded Chinese strings in source files.
- Notifications follow selected language.
- Browser dashboard follows selected language.
- Tests cover i18n key existence and language switching.

---

## Workstream H — Open-source release readiness

### Goal

Prepare the repository for public GitHub release.

### Required files

Add or update:

- `README.md`
- `README.zh-CN.md`
- `LICENSE`
- `AI_DISCLOSURE.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `CODE_OF_CONDUCT.md` if appropriate
- `docs/INSTALL.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `SOURCE_GUIDE.md`
- `NOTIFICATION_GUIDE.md`
- `.env.example`
- `config.example.yaml`
- `.gitignore`

### README requirements

Both README files should explain:

- What this project is
- What it is not
- Main features
- Quick start
- Configuration
- Local server usage
- Source setup
- Notification setup
- Language switching
- Security/privacy notes
- Troubleshooting
- Roadmap
- License
- AI-assisted development disclosure
- Financial-advice disclaimer

### Required disclaimers

Include in English README and Chinese README:

- This software is for news monitoring and information delivery only.
- It does not provide financial advice.
- It does not execute trades.
- Users are responsible for their own decisions.
- It does not bypass paywalls, simulate logins, or scrape private content.
- Personal WeChat/QQ notifications depend on third-party relay services if enabled.

### Acceptance criteria

- Repository looks publishable.
- Documentation is bilingual and coherent.
- GPL-3.0-only license exists.
- AI disclosure exists.
- No private data/secrets in examples.

---

## Workstream I — Code quality, maintainability, and performance

### Goal

Clean the codebase for open-source maintainability.

### Requirements

1. Remove dead code.
2. Reduce duplication.
3. Keep source code English-only.
4. Use clear module boundaries.
5. Keep source fetchers consistent.
6. Keep notifiers consistent.
7. Keep config parsing consistent.
8. Avoid unnecessary dependencies.
9. Avoid artificial delays.
10. Mask secrets in logs.
11. Keep logging structured and useful.
12. Add type hints where practical.
13. Ensure code is readable by future contributors.

### Tooling

Add or improve:

- `ruff`
- `black`
- `pytest`
- `pytest-cov` if practical
- `pre-commit` if practical
- `mypy` or `pyright` only if it does not create excessive churn

Do not over-engineer.

### Acceptance criteria

- Formatting/lint checks are available.
- Tests pass.
- Secrets are masked in logs.
- Code remains easy to read.
- No Chinese text in source files.

---

## Workstream J — GitHub Actions

### Goal

Add open-source-ready GitHub Actions.

### Required workflows

#### `.github/workflows/ci.yml`

Run on push and pull request.

Should perform:

- Checkout
- Setup Python
- Cache dependencies
- Install dependencies
- Run `ruff`
- Run `black --check`
- Run `pytest`
- Run `python -m compileall src tests`
- Validate `config.example.yaml`
- Validate `.env.example`
- Run a basic no-secret check

#### `.github/workflows/build.yml`

Build artifacts for:

- `macos-latest`
- `windows-latest`

Artifacts:

- `AI-News-Monitor-macOS.zip`
- `AI-News-Monitor-Windows.zip`

Each artifact should include:

- App/executable
- README.md
- README.zh-CN.md
- LICENSE
- AI_DISCLOSURE.md
- SOURCE_GUIDE.md
- NOTIFICATION_GUIDE.md
- config.example.yaml
- .env.example

#### `.github/workflows/release.yml`

When a version tag such as `v0.9.0` is pushed:

- Run tests
- Build macOS artifact
- Build Windows artifact
- Create or update GitHub Release
- Upload artifacts

#### Optional docs/security workflow

If practical, add a workflow or CI step checking:

- Required docs exist
- `.env` not committed
- `config.yaml` not committed
- logs/data not committed
- obvious API key patterns absent

### Acceptance criteria

- CI exists and is documented.
- Build workflows exist.
- Release workflow exists or is clearly scaffolded.
- Workflows do not require real user secrets.
- Windows path exists even if local validation is not possible.

---

## Workstream K — Build and deployment

### Goal

Make installation and deployment simple.

### Requirements

1. macOS PyInstaller build should work.
2. Windows PyInstaller build path should work or be clearly documented and tested through GitHub Actions.
3. Artifacts should include all necessary examples and docs.
4. First-run setup should not require manual YAML editing for normal users.
5. Optional advanced config via YAML remains available.

### Documentation

Add or update:

- `docs/INSTALL.md`
- Packaging instructions
- First-run instructions
- Windows notes
- macOS notes
- Troubleshooting

### Acceptance criteria

- macOS build works.
- Windows build workflow exists.
- Artifacts are user-friendly.
- README can guide non-expert setup.

---

## Workstream L — E2E and regression tests

### Goal

Increase confidence that the app works end-to-end.

### Required tests

Add or improve tests for:

1. Fast Alert formatting
2. Full Analysis formatting
3. No Chinese in source code files except allowed resource/docs files
4. README language switch links
5. GPL license file exists
6. AI disclosure file exists
7. Config example parses
8. Source library parsing
9. Source wizard validation
10. Source health state
11. Custom source add/remove persistence
12. Quality scoring with official/multi-source/blacklist/whitelist behavior
13. Notification retry/backoff
14. Notification fallback
15. Notifier health state
16. Mock RSS → monitor cycle → mock LLM → alert saved → mock notifier sent
17. SSE event emission
18. Browser dashboard health/status endpoints
19. Language filter: Chinese/English only
20. i18n key coverage
21. Config save/reload
22. Secret masking in logs

### Acceptance criteria

- Existing tests still pass.
- New tests pass.
- CI can run tests without real keys.
- Tests do not require real network unless explicitly marked integration/optional.

---

# Implementation process

Follow this process:

1. Read all required project files.
2. Inspect architecture.
3. Produce a milestone implementation plan.
4. Implement in small batches.
5. Run relevant tests after each batch.
6. Update tests with each feature.
7. Update documentation.
8. Run final tests.
9. Run final open-source readiness audit.
10. Report results.

Do not make unrelated rewrites.
Do not add heavy dependencies without justification.
Do not degrade current working behavior.

---

# Final audit report format

At completion, output:

```text
## Completed
- ...

## Partially completed
- ...

## Not completed / blocked
- ...

## Tests run
- ...

## Build results
- ...

## GitHub Actions added
- ...

## Open-source readiness
- ...

## UI/UX improvements
- ...

## Important files changed
- ...

## Remaining risks
- ...

## Recommended next step
- ...
```

---

# Definition of done

This iteration is complete only when:

- The local browser console is significantly more useful and modern.
- The UI is visually and structurally upgraded while remaining lightweight.
- Fast Alert is default and source-first.
- Full Analysis is optional.
- Source Library is expanded, grouped, testable, and user-editable.
- Every required user-provided credential/source field has helper links.
- Notification Center shows health and supports retry/fallback.
- Chinese/English i18n is complete through resource files.
- Source code contains no Chinese text except allowed resource/docs files.
- README supports English/Chinese switching.
- Repository is prepared for public GitHub release under GPL-3.0-only.
- AI disclosure exists.
- GitHub Actions exist for CI, build, and release.
- Tests cover core E2E behavior.
- No secrets are hard-coded or committed.
