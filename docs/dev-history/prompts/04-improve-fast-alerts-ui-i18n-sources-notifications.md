# AI News Monitor — Next Iteration Codex Goal Prompt

## How to use this file

From the repository root, run Codex CLI with this archived prompt:

```text
/goal Read ./docs/dev-history/prompts/04-improve-fast-alerts-ui-i18n-sources-notifications.md carefully and implement everything described in it. Treat this file as the authoritative next-iteration product and engineering specification. Before coding, read HANDOFF.md, README.md, config.example.yaml, and tests/test_next_phase_features.py. Work in focused milestones, run tests after each milestone, avoid hard-coding secrets, and finish with a requirement-by-requirement audit.
```

## Mission

The current project has reached a working phase: it can run as a local 24/7 news monitor, fetch public news sources, filter articles, use an LLM for translation/summarisation/analysis, deliver notifications, and expose a local desktop/server UI.

This next iteration must **narrow the product direction** and improve usability, information quality, source coverage, delivery reliability, UI quality, and test coverage.

The product must not become an automatic trading or decision-making tool. Its purpose is:

> Given user-defined key information, prompts, and keywords, continuously monitor enough high-quality Chinese and English information sources worldwide, find items close to the user’s needs, and deliver timely, high-quality information to the user through convenient ports such as email and messaging apps. The user will perform deeper analysis manually.

The application should be primarily self-hosted on the user’s laptop/desktop as a temporary local server. The user should be able to view the most complete feedback locally, edit destinations, input API keys, manage sources, tune necessary parameters, and keep the app running 24/7 with minimal friction.

---

# Product Principles

## 1. Timeliness first

The most important value of this app is **24/7 near-real-time discovery**.
The system should detect relevant news quickly and deliver it promptly to the user’s chosen channels.

Do not over-optimise for deep analysis if that delays delivery. Prefer fast, source-grounded, concise alerts.

## 2. High-quality information, not AI over-analysis

The user wants high-quality original information delivered quickly.
LLM output should help with comprehension, translation, and concise summarisation, but it must not dominate the alert.

Default alert mode should be **Fast Alert Mode**, not Full Analysis Mode.

### Fast Alert Mode should include

- Article title
- Translated title if needed
- Original source
- Published time
- Original link
- Short summary
- Why it matched the user’s prompt or keywords
- Matched keywords/entities
- Source reliability/context
- Cluster/context if multiple sources cover the same event

### Full Analysis Mode should be optional

Only if enabled by the user, include:

- Why it matters
- Possible market relevance
- Bullish/bearish paths
- Risks
- Uncertainty notes
- Watchlist/stocks

The app must never present stock-related observations as financial advice.

## 3. Chinese and English only

The system must support:

- Input prompts and keywords in Chinese and English
- News sources in Chinese and English only
- Output language switching between Chinese and English

Do not monitor or process sources in other languages unless the user later explicitly enables them.

## 4. User-controlled, local-first, easy deployment

The default usage scenario is:

- The app runs on the user’s own laptop/desktop as a local server
- The user opens the UI locally
- The user enters API keys, notification endpoints, prompts, and source settings
- The system runs continuously and sends alerts to phone-friendly channels

Deployment should be simple:

- Windows: unzip/run executable
- macOS: unzip/run app or executable
- No mandatory Docker for normal users
- Docker/VPS deployment can be documented as optional

## 5. No hard-coded secrets

Never hard-code:

- LLM API keys
- Email passwords
- SMTP credentials
- Webhook URLs
- Telegram tokens
- WeCom URLs
- ServerChan/Chanify/Qmsg keys
- Any user prompt or private destination

Use `.env`, local config, or secure local settings only. Ensure `.env`, `config.yaml`, logs, databases, and local runtime files remain ignored by git.

---

# Must-read files before implementation

Before making changes, read these files in order:

1. `HANDOFF.md`
2. `README.md`
3. `config.example.yaml`
4. `tests/test_next_phase_features.py`

Then inspect the relevant implementation files, especially:

- `src/ai_news_monitor/monitor.py`
- `src/ai_news_monitor/config.py`
- `src/ai_news_monitor/models.py`
- `src/ai_news_monitor/scoring.py`
- `src/ai_news_monitor/bias.py`
- `src/ai_news_monitor/translation.py`
- `src/ai_news_monitor/language.py`
- `src/ai_news_monitor/realtime.py`
- `src/ai_news_monitor/notifiers/`
- `src/ai_news_monitor/sources/`
- `src/ai_news_monitor/ui/`

Start by producing a short internal implementation plan, then implement the changes.

---

# Current Pain Points to Fix

## UI pain points

The current UI has these issues:

- Too bright/glare-prone in places
- Content is too scattered
- Colours are too monotonous
- Settings page relies too much on box/frame structures with low usability
- Text formatting is rigid and old-fashioned
- Layout is not modern, modular, or flat enough
- Other pages have similar issues
- Some settings feel like raw developer forms instead of a consumer-grade configuration experience

The UI must be redesigned to feel:

- Lightweight
- Apple-inspired
- Minimalist
- Modern
- Modular
- Flat
- Calm but not boring
- Clear and fast to operate

## Configuration pain points

Fields requiring human-provided information are not helpful enough.
Hiding secrets is not enough.

For every field where the user must obtain information elsewhere, the UI must provide:

- A short explanation of what the value is
- A direct official/help URL or button to obtain it
- A test/verify action where feasible
- Clear success/failure feedback
- Minimal required fields by default
- Advanced fields hidden behind an “Advanced” section

This especially applies to:

- LLM API key
- LLM base URL/model
- Email SMTP/app password
- Telegram bot token/chat ID
- WeCom webhook
- WeChat relay key/webhook
- QQ relay key/webhook
- Generic webhook
- RSS/Atom feed URL
- Official source URLs
- Custom source metadata

---

# Scope for This Iteration

Implement the following workstreams.

---

## Workstream A — Fast Alert Mode and Information Delivery UX

### Objective

Make the product default to fast, high-quality information delivery rather than over-analysis.

### Requirements

1. Add an alert mode setting:

```yaml
alerts:
  default_mode: "fast"   # fast | full_analysis
```

2. In Fast Alert Mode, notification content should focus on:

- Title
- Translated title if applicable
- Source
- Published time
- Original URL
- Short summary
- Match reason
- Matched keywords/entities
- Source reliability/context
- Clustered coverage if available

3. In Full Analysis Mode, keep the richer LLM analysis fields if they already exist, but make them clearly optional.

4. Update the notification formatter so that Fast Alert Mode is the default for all channels.

5. Ensure the UI allows the user to switch alert mode.

6. Update README and config examples.

### Acceptance criteria

- Fast alerts are concise and source-first.
- Full analysis can still be enabled.
- No alert makes financial-advice style claims.
- Tests verify that Fast Alert Mode omits unnecessary deep analysis fields.

---

## Workstream B — Full UI Redesign

### Objective

Upgrade the visual and interaction design across all pages.

### Requirements

1. Redesign the UI with Apple-inspired principles:

- Large clear headings
- Soft neutral background
- Strong but restrained typography
- Modular cards instead of heavy frames
- Subtle shadows/borders
- More whitespace
- Less visual clutter
- Gentle accent colour
- Better spacing hierarchy
- Clear primary/secondary actions

2. Reduce glare:

- Avoid harsh pure-white full-screen areas where possible
- Use soft off-white / light grey backgrounds
- Support a comfortable light theme
- If feasible, add a dark mode or low-glare mode

3. Replace rigid form layouts where possible with modular sections:

- Dashboard cards
- Settings cards
- Source cards
- Notifier cards
- Status/health cards

4. Improve the Settings page:

- Reorganise settings into clear modules:
  - General
  - Language
  - LLM
  - Alerts
  - Sources
  - Notifications
  - Local Server
  - Advanced
- Hide advanced fields by default.
- Make each module independently testable/savable where feasible.
- Reduce long walls of form controls.

5. Improve text formatting:

- Use clearer hierarchy: title, subtitle, helper text, field labels, inline hints.
- Use concise microcopy.
- Avoid dense paragraphs inside forms.
- Use modern bilingual labels where needed.

6. Improve animations:

- Add subtle, natural animations for page transitions, card expansion, notifications, and dialogs.
- Animations must be lightweight and never block user interaction.
- Respect performance and avoid excessive motion.

7. Modernise dialogs:

- Use consistent modern modal/dialog styling.
- Error, success, warning, and confirmation dialogs should be visually clear and bilingual.
- Dialogs should not feel like default OS message boxes unless unavoidable.

### Acceptance criteria

- UI feels more modern, modular, flat, and Apple-like.
- Settings no longer feels like a raw form dump.
- All pages follow a consistent visual system.
- Animations are subtle and do not slow the app.
- UI remains responsive on typical laptops.

---

## Workstream C — Complete Chinese/English i18n

### Objective

Guarantee that once a language is selected, the entire app and all output are unified in that language.

### Requirements

1. The app must support two UI/output languages:

```yaml
app:
  output_language: "zh-CN"  # zh-CN | en
```

2. The global language toggle must affect:

- Desktop UI
- Browser/local server dashboard
- Notifications
- Logs shown in UI
- Error messages
- Dialogs
- Settings labels
- Source manager text
- Notifier manager text
- Help text/tooltips
- Alert summaries generated by LLM
- Any scripted/system output visible to the user

3. Replace all hard-coded Chinese or English UI strings with i18n keys.

4. Ensure SettingsPage and all form labels are fully internationalised.

5. Switching language should apply immediately where possible without restart.

6. Input news sources remain limited to Chinese and English.

7. Prompts can be Chinese or English.

### Acceptance criteria

- Tests or UI checks verify language toggle affects Dashboard, Topics, Settings, Logs, source management, notifier settings, dialogs, and browser dashboard.
- No obvious hard-coded language fragments remain in UI files.
- Notifications follow the selected output language.

---

## Workstream D — Source Library and Source Management

### Objective

Turn the source layer from a minimal editable list into a high-quality, user-editable source library.

### Current known sources

Current source types include:

- GDELT
- Google News RSS
- Yahoo Finance RSS
- Public RSS
- Official RSS
- Custom RSS

Current defaults are not enough for the product goal. They include a few tech/AI-oriented sources, but not enough Chinese, Taiwan, US policy, semiconductor, official, financial, or company IR sources.

### Requirements

1. Create a modern **Source Library** UI.

2. Group sources into categories:

- Global News
- Finance
- Official / Government
- China
- Taiwan
- US
- Semiconductor / AI
- Company IR
- Custom

3. Each source should be displayed as a card with:

- Source name
- Language: Chinese or English
- Type: RSS, API, official press release, company IR, custom
- Reliability score
- Ownership/publisher
- Bias/context hint
- Enabled/disabled toggle
- Last fetch time
- Last success/failure state
- Failure reason if any
- Test source button
- Source website/help URL

4. Add a source wizard:

Step 1: Choose source type
Step 2: Enter URL
Step 3: Test URL
Step 4: Auto-detect name/language/feed sample where feasible
Step 5: Confirm category/reliability/metadata

5. Provide direct guidance for every user-needed input:

- “Where do I find an RSS feed?”
- “Open source website”
- “Test feed”
- “View examples”
- “What is reliability score?”

6. Expand the default source library to at least 30 curated optional sources, but do not enable all by default.

7. Default enabled sources should be few but high-quality.

8. The app must not scrape paywalled content, simulate logins, bypass access controls, or use unauthorised sources.

9. Support only public RSS/Atom feeds, public APIs, official press-release pages that are allowed, and company IR feeds/pages that are publicly accessible.

10. Preserve user custom sources across restarts.

### Recommended source categories to include

Do not blindly add invalid URLs. Verify feed URLs when possible. If an official source does not provide RSS, include it as a disabled website/source candidate with instructions.

Suggested candidates:

#### Global / English

- Google News RSS
- GDELT
- Yahoo Finance RSS
- Associated Press if public RSS is available
- Reuters only if public RSS or legally accessible feed is available
- CNBC RSS if public
- MarketWatch RSS if public
- BBC News RSS if public
- The Guardian RSS if public
- TechCrunch
- The Verge
- Ars Technica

#### Official / Government

- White House
- US Department of Commerce
- US Department of State
- US Treasury
- SEC
- Taiwan Presidential Office
- Taiwan Ministry of Economic Affairs
- Taiwan Financial Supervisory Commission
- China State Council / 中国政府网
- China Ministry of Commerce / 商务部

#### Taiwan / Chinese

- Central News Agency / 中央社
- Taiwan Economic Daily / 經濟日報 if public feed exists
- Commercial Times / 工商時報 if public feed exists
- Other reputable public Chinese feeds with stable RSS

#### Semiconductor / AI / Company IR

- TSMC Investor Relations / Newsroom
- NVIDIA Newsroom
- ASML News
- Applied Materials News
- AMD Newsroom
- Intel Newsroom
- Broadcom News
- Semiconductor Engineering if public RSS exists
- arXiv cs.AI
- TechCrunch AI

### Acceptance criteria

- User can enable/disable sources from UI.
- User can add/test/remove custom sources.
- Source cards show status and helpful metadata.
- There are enough curated optional source candidates to make the product useful beyond the MVP.
- Source settings persist.
- Tests cover source config parsing and custom source addition.

---

## Workstream E — Required-Information Helper Links

### Objective

Every field that requires the user to obtain external credentials or URLs must provide direct help.

### Requirements

Add helper links/buttons for:

1. LLM API

- OpenAI API keys page
- OpenAI-compatible base URL explanation
- Model selection explanation
- Test LLM connection button

2. Email

- Gmail App Password help
- Outlook/SMTP help if applicable
- SMTP host/port explanation
- Test email button

3. Telegram

- BotFather link/instructions
- How to get chat ID
- Test Telegram button

4. WeCom

- WeCom group bot webhook instructions
- Test WeCom button

5. WeChat personal relay

- ServerChan / Server酱 instructions
- Chanify instructions if supported
- Explain that direct personal WeChat bot APIs are not officially reliable
- Test WeChat relay button

6. QQ relay

- Qmsg or other supported relay service instructions if supported
- Explain limitations and stability dependencies
- Test QQ relay button

7. Sources

- RSS/Atom explanation
- Feed test button
- Example source library
- Official website link
- Explain allowed public sources vs unsupported paywalled/private sources

### Acceptance criteria

- UI contains helper links for all credential/source fields.
- Users can test every configured channel.
- Validation prevents enabling incomplete channels.
- Error messages are friendly and actionable.

---

## Workstream F — Notification Channel Stability and Fallback

### Objective

Make notification delivery reliable for long-running use.

### Requirements

1. For each notifier, track:

- Configured/unconfigured
- Enabled/disabled
- Last success time
- Last failure time
- Failure count
- Last error message
- Health status
- Test result

2. Implement retry with exponential backoff for notification failures.

3. Implement optional fallback routing:

```yaml
notifications:
  fallback_enabled: true
  fallback_order:
    - email
    - telegram
    - wecom
    - wechat_relay
    - qq_relay
    - generic_webhook
```

4. If the primary notifier fails, try fallback channels if enabled.

5. Surface health status in UI as notifier cards.

6. Make test notifications easy and safe.

7. Ensure WeChat/QQ relay integrations are honest about limitations. If stable direct implementation is not feasible, implement generic relay/webhook mode and document the setup.

### Acceptance criteria

- Health cards show notifier state.
- Fallback routing works in tests.
- Retries/backoff are tested.
- Users can quickly identify broken notification ports.

---

## Workstream G — Information Quality Scoring

### Objective

Improve the quality of delivered information without relying too heavily on LLM analysis.

### Requirements

Enhance ranking/scoring to consider:

- Keyword/prompt match strength
- Recency
- Source reliability
- Official source boost
- Same-event multi-source confirmation boost
- Source category priority
- User whitelist/blacklist
- Duplicate/rewritten-source penalty
- Low-quality aggregator penalty
- Language match/preference
- Whether the item includes an original source link

Add config fields:

```yaml
quality:
  official_source_boost: 0.10
  multi_source_confirmation_boost: 0.15
  low_quality_source_penalty: 0.20
  whitelist_boost: 0.20
  blacklist_exclude: true
```

Keep scoring explainable. In the UI and notifications, include a short “why this was selected” explanation.

### Acceptance criteria

- Scoring produces explainable results.
- Multi-source confirmation improves score.
- Blacklisted sources are excluded.
- Whitelisted/official sources rank higher.
- Tests cover scoring behavior.

---

## Workstream H — Local Server and Live Feedback

### Objective

Improve local server usability as the operator’s main monitoring surface.

### Requirements

1. Improve the local browser dashboard at `http://localhost:<port>`.

2. It should show:

- Running status
- Last fetch time
- Processed articles
- Matched articles
- Sent alerts
- Queue length
- Source health
- Notifier health
- Recent alerts
- Recent errors
- SSE connection status
- Current language/output mode

3. Keep it lightweight.

4. Add real-time updates via SSE/WebSocket.

5. If port is occupied, provide a clear error and optionally try the next available port.

6. Document LAN access carefully. Default should remain local-only.

### Acceptance criteria

- Local dashboard is useful and visually consistent.
- SSE connection works and reconnects.
- Port errors are handled gracefully.
- Tests cover health/status endpoints where feasible.

---

## Workstream I — E2E and Regression Tests

### Objective

Move beyond unit-only verification and add end-to-end confidence.

### Required tests

Add or improve tests for:

1. Fast Alert Mode formatting
2. Full Analysis Mode optional formatting
3. UI i18n coverage or string key coverage
4. Settings save/reload consistency
5. Source library parsing and source wizard validation
6. Source deduplication
7. Enhanced quality scoring
8. Notification health status
9. Retry/backoff behavior
10. Fallback notification routing
11. Mock RSS → monitor cycle → mock LLM → alert saved → mock notifier sent
12. SSE event emission
13. Language filtering: Chinese/English only
14. Browser dashboard health/status endpoints
15. Config examples remain valid

### Acceptance criteria

- Existing tests still pass.
- New tests pass.
- Add a final verification checklist to README or HANDOFF.

---

## Workstream J — Build and Deployment

### Objective

Make deployment simple and reliable.

### Requirements

1. Ensure PyInstaller packaging still works for macOS.

2. Add/repair Windows packaging path.

3. Ensure GitHub Actions can build:

- macOS artifact
- Windows artifact

4. Ensure artifacts include:

- Executable/app
- README
- config.example.yaml
- .env.example
- Source setup guide
- Notification setup guide

5. Update README with:

- First run instructions
- How to configure LLM
- How to configure email
- How to configure Telegram/WeCom/WeChat/QQ relay
- How to add news sources
- How to switch language
- How to run as a local server
- How to check logs
- Troubleshooting

6. If Windows cannot be verified locally, document exact validation steps and mark it honestly.

### Acceptance criteria

- macOS build works.
- Windows build path exists and is documented.
- README is clear enough for a non-expert user.
- No secrets are included in artifacts.

---

# Implementation Process

Follow this process:

1. Read required files.
2. Inspect architecture.
3. Create a short implementation plan with milestones.
4. Implement changes in small batches.
5. Run tests after each batch.
6. Add or update tests for each new capability.
7. Update README, HANDOFF, config.example.yaml, and any relevant docs.
8. Run final tests.
9. Produce final audit.

Do not make large unrelated rewrites unless necessary.

---

# Final Audit Format

At the end, produce a report with this structure:

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

## Important files changed
- ...

## User-visible improvements
- ...

## Remaining risks
- ...

## Recommended next step
- ...
```

---

# Definition of Done

This iteration is complete only when:

- Fast Alert Mode is default and works.
- Full Analysis Mode is optional.
- UI is visibly more modern, modular, flatter, less glaring, and easier to use.
- All user-required credentials/source fields have direct helper links and tests.
- UI and notifications are fully bilingual in Chinese/English.
- Source Library exists with grouped curated sources and editable custom sources.
- Notification health, retry, and fallback are implemented.
- Quality scoring is improved and explainable.
- Local server dashboard is more useful.
- E2E/regression tests cover the new behavior.
- Packaging remains available for macOS and Windows path is documented/implemented.
- No secrets are hard-coded or committed.
