# Prompt

This file consolidates the historical development prompts in their original sequence. These prompts are project history only and are not required for normal installation or use.

## Contents

1. [Initial AI News Monitor prompt](#01-initial-ai-news-monitor-prompt)
2. [Next-phase product prompt](#02-next-phase-product-prompt)
3. [Update prompt](#03-update-prompt)
4. [Next-iteration prompt](#04-next-iteration-prompt)
5. [Final target candidate prompt](#05-final-target-candidate-prompt)
6. [Pre-GitHub interface stabilization prompt](#06-pre-github-interface-stabilization-prompt)
7. [Source reliability and freshness prompt](#07-source-reliability-and-freshness-prompt)
8. [GitHub upload readiness prompt](#08-github-upload-readiness-prompt)
9. [E2E operational closure prompt](#09-e2e-operational-closure-prompt)
10. [Final GitHub upload cleanup prompt](#10-final-github-upload-cleanup-prompt)
11. [Phase verification prompt](#11-phase-verification-prompt)

---

## 01. Initial AI News Monitor prompt

Source file before consolidation: `01-codex_prompt_ai_news_monitor.md`

# Codex Prompt: Build a Lightweight 24/7 AI News Monitor Desktop App

You are Codex acting as a senior full-stack Python desktop application engineer. Build a production-quality, lightweight, cross-platform desktop application called **AI News Monitor**.

The app monitors free public news sources 24/7, analyzes news against user-defined prompts using a user-provided LLM API, and pushes summaries + links + LLM-generated market-watch suggestions to user-configured destinations such as Email, WeCom, Telegram, or a generic webhook.

Do **not** build an auto-trading app. Do **not** connect to brokerage APIs for order placement. This is an alerting and analysis tool only.

---

## 1. Product Goal

Build a lightweight desktop app for Windows and macOS that lets a user:

1. Enter or update an LLM API configuration.
2. Enter or update one or more notification destinations:
   - Email via SMTP
   - WeCom / Enterprise WeChat webhook
   - Telegram bot
   - Generic custom webhook API
3. Enter, edit, pause, resume, or delete monitoring prompts/topics while the app is running.
4. Run the monitor continuously 24/7 while the computer is on.
5. Receive timely alerts when relevant free public news is found.
6. Receive each alert with:
   - original news title
   - original news links
   - source name
   - published time if available
   - LLM-generated summary
   - LLM-generated relevance explanation
   - LLM-generated related-stock/watchlist suggestions
   - LLM-generated bullish and bearish scenario analysis
   - risk notes / uncertainty notes
7. Pause, resume, or terminate monitoring clearly from the UI.
8. See fast, clear operational feedback in the UI: running status, last fetch time, last alert time, recent logs, and errors.

The final product should be easy to upload to GitHub, easy to deploy on Windows/macOS, and easy to extend in future versions.

---

## 2. Non-Negotiable Security Requirements

Never hardcode any user secrets or personal prompts in the source code.

The following must **never** be written into source files, commits, build scripts, GitHub Actions, or release artifacts:

- LLM API keys
- email passwords or app passwords
- SMTP credentials
- WeCom webhook URLs
- Telegram bot tokens
- Telegram chat IDs
- generic webhook tokens
- user-defined prompts/topics
- user email addresses, except placeholders in example files

Use only example placeholder files in the repository:

- `.env.example`
- `config.example.yaml`

Real local runtime files must be ignored by Git:

- `.env`
- `config.yaml`
- `user_config.yaml`
- `data/`
- `logs/`
- `*.sqlite`
- build artifacts
- local caches

Add these to `.gitignore`.

Secrets should be loaded from environment variables and/or a local `.env` file. User prompts and topic definitions should be loaded from a local YAML configuration file and editable through the UI.

The app must mask secrets in the UI, never print secrets in logs, never send secrets to the LLM, and never include secrets in notification content.

---

## 3. Recommended Tech Stack

Use this stack unless there is a strong technical reason to change it:

- Language: Python 3.11+
- UI: PySide6 / Qt for Python
- HTTP: `httpx`
- RSS parsing: `feedparser`
- HTML cleanup: `beautifulsoup4` if needed
- Config: `PyYAML`, `python-dotenv`
- Database: SQLite using Python stdlib `sqlite3`
- Scheduling/background work: a dedicated worker thread that does not block the UI
- Testing: `pytest`
- Packaging: PyInstaller
- CI/build: GitHub Actions for Windows and macOS builds

Keep the app lightweight. Do not use Electron. Do not add unnecessary heavy dependencies.

---

## 4. App Architecture

Use a clean modular structure similar to this:

```text
ai-news-monitor/
├─ README.md
├─ LICENSE
├─ .gitignore
├─ .env.example
├─ config.example.yaml
├─ requirements.txt
├─ pyproject.toml                 # optional but preferred if helpful
├─ main.py
├─ src/
│  ├─ app.py
│  ├─ config.py
│  ├─ secrets.py
│  ├─ models.py
│  ├─ monitor.py
│  ├─ scheduler.py
│  ├─ dedupe.py
│  ├─ llm_client.py
│  ├─ scoring.py
│  ├─ logging_setup.py
│  ├─ ui/
│  │  ├─ main_window.py
│  │  ├─ dashboard_page.py
│  │  ├─ topics_page.py
│  │  ├─ settings_page.py
│  │  ├─ logs_page.py
│  │  └─ widgets.py
│  ├─ sources/
│  │  ├─ base.py
│  │  ├─ gdelt.py
│  │  ├─ google_news_rss.py
│  │  ├─ yahoo_finance_rss.py
│  │  └─ official_rss.py
│  ├─ notifiers/
│  │  ├─ base.py
│  │  ├─ email_notifier.py
│  │  ├─ wecom_notifier.py
│  │  ├─ telegram_notifier.py
│  │  └─ generic_webhook_notifier.py
│  └─ utils/
│     ├─ time_utils.py
│     ├─ text_utils.py
│     └─ url_utils.py
├─ tests/
│  ├─ test_config.py
│  ├─ test_dedupe.py
│  ├─ test_llm_schema.py
│  ├─ test_notifiers.py
│  └─ test_sources.py
├─ scripts/
│  ├─ build_windows.ps1
│  └─ build_macos.sh
└─ .github/
   └─ workflows/
      └─ build-release.yml
```

If you simplify the structure, preserve modularity and future extensibility.

---

## 5. User Experience and UI Requirements

Build a modern, minimal, fast desktop UI. The UI should feel simple and clean, not like a developer console.

Default UI language: Chinese Simplified for user-facing text. Keep internal code and comments in English.

### Main UI pages

#### 5.1 Dashboard

Show:

- Overall status: Running / Paused / Stopped / Error
- Current active topics count
- Last fetch time
- Last successful source fetch
- Last LLM analysis time
- Last alert sent time
- Number of articles fetched in the latest cycle
- Number of candidate articles after keyword filtering
- Number of alerts sent today
- Recent alert cards
- Clear buttons:
  - Start
  - Pause
  - Resume
  - Stop
  - Send Test Notification

The UI must respond quickly. Network operations must never freeze the UI.

#### 5.2 Topics / Prompt Editor

Allow the user to create, edit, pause, resume, and delete monitoring topics.

Each topic should include:

- topic name
- enabled/disabled toggle
- free-form user prompt
- keywords / phrases
- related stock/watchlist candidates
- preferred output language, default `zh-CN`
- minimum relevance score threshold
- poll interval override, optional
- cooldown period, optional
- official RSS URLs, optional

The user must be able to modify prompts while the monitor is running. Changes should take effect on the next monitoring cycle without restarting the app.

Include validation:

- topic name required
- prompt required
- at least one keyword required unless the user explicitly enables broad search mode
- threshold must be 0-100
- invalid URLs rejected with friendly messages

#### 5.3 Settings

Sections:

1. LLM Settings
   - provider name
   - OpenAI-compatible base URL
   - model name
   - API key, masked
   - max tokens
   - temperature
   - timeout
   - Test LLM button

2. Email Settings
   - enabled toggle
   - SMTP host
   - SMTP port
   - TLS/SSL setting
   - username
   - app password, masked
   - from address
   - to addresses
   - Test Email button

3. WeCom Settings
   - enabled toggle
   - webhook URL, masked
   - Test WeCom button

4. Telegram Settings
   - enabled toggle
   - bot token, masked
   - chat ID, masked if appropriate
   - Test Telegram button

5. Generic Webhook Settings
   - enabled toggle
   - webhook URL, masked
   - method: POST by default
   - optional custom headers as key-value pairs
   - optional JSON body template
   - Test Webhook button

6. Runtime Settings
   - default poll interval
   - max alerts per hour
   - deduplication window
   - log retention days
   - run minimized to tray toggle if feasible

#### 5.4 Logs

Show recent logs with filters:

- Info
- Warning
- Error
- Alerts

Include a button to open the logs folder.

### System tray

If feasible with PySide6, support minimizing to system tray with menu actions:

- Show app
- Pause monitoring
- Resume monitoring
- Stop monitoring
- Quit

If tray support is unreliable, keep it simple and do not overcomplicate the MVP. But the app should continue running while minimized.

---

## 6. Configuration and Runtime Storage

Support both portable mode and app-data mode.

Priority:

1. If `config.yaml` and `.env` exist beside the executable, use them. This is portable mode.
2. Otherwise use an app data directory:
   - Windows: `%APPDATA%/AI News Monitor/`
   - macOS: `~/Library/Application Support/AI News Monitor/`

The UI should create missing local config files on first launch by copying from examples or writing safe defaults.

Example `config.example.yaml`:

```yaml
app:
  output_language: "zh-CN"
  portable_mode: true

monitor:
  default_interval_seconds: 120
  min_relevance_score: 80
  max_alerts_per_hour: 5
  deduplicate_hours: 72
  request_timeout_seconds: 20

llm:
  provider: "openai_compatible"
  base_url: "https://api.openai.com/v1"
  model: "gpt-4.1-mini"
  api_key_env: "LLM_API_KEY"
  temperature: 0.2
  max_tokens: 1200
  timeout_seconds: 30

sources:
  gdelt:
    enabled: true
  google_news_rss:
    enabled: true
  yahoo_finance_rss:
    enabled: true
  official_rss:
    enabled: true
    urls: []

notifiers:
  email:
    enabled: true
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    use_tls: true
    username_env: "EMAIL_USERNAME"
    password_env: "EMAIL_APP_PASSWORD"
    from_addr_env: "EMAIL_FROM"
    to_addrs:
      - "your_email@example.com"

  wecom:
    enabled: false
    webhook_url_env: "WECOM_WEBHOOK_URL"

  telegram:
    enabled: false
    bot_token_env: "TELEGRAM_BOT_TOKEN"
    chat_id_env: "TELEGRAM_CHAT_ID"

  generic_webhook:
    enabled: false
    url_env: "GENERIC_WEBHOOK_URL"
    method: "POST"
    headers: {}
    body_template: "default"

topics:
  - name: "Trump Taiwan business cooperation"
    enabled: true
    output_language: "zh-CN"
    min_relevance_score: 80
    cooldown_minutes: 30
    prompt: >
      Monitor whether Trump visits Taiwan or announces concrete commercial,
      semiconductor, defense, AI, chip supply-chain, manufacturing, or trade
      cooperation with Taiwan. Only alert if the news is recent, concrete,
      market-relevant, and supported by at least one source link. Summarize the
      event, explain why it matters, suggest related watchlist stocks, and give
      both bullish and bearish risk paths.
    keywords:
      - "Trump Taiwan"
      - "Trump visits Taiwan"
      - "US Taiwan semiconductor cooperation"
      - "Taiwan defense deal"
      - "TSMC Nvidia"
      - "Taiwan trade deal"
      - "特朗普 台湾"
      - "台湾 半导体 合作"
    related_stocks:
      - "TSM"
      - "NVDA"
      - "ASML"
      - "AMAT"
      - "LRCX"
      - "KLAC"
      - "EWT"
      - "LMT"
      - "RTX"
    official_rss_urls: []
```

Example `.env.example`:

```env
LLM_API_KEY=replace_me
EMAIL_USERNAME=replace_me
EMAIL_APP_PASSWORD=replace_me
EMAIL_FROM=replace_me
WECOM_WEBHOOK_URL=replace_me
TELEGRAM_BOT_TOKEN=replace_me
TELEGRAM_CHAT_ID=replace_me
GENERIC_WEBHOOK_URL=replace_me
```

---

## 7. Free News Sources Only

Do not use paid news APIs or paid news terminals.

Implement adapters for free/public sources:

1. GDELT
2. Google News RSS keyword feeds
3. Yahoo Finance RSS / public finance news feeds where feasible
4. Official RSS URLs configured by the user

The source adapters should implement a common interface:

```python
class NewsSource:
    name: str
    def fetch(self, topic: TopicConfig) -> list[Article]:
        ...
```

Each `Article` should include:

```python
@dataclass
class Article:
    title: str
    url: str
    source: str
    published_at: datetime | None
    snippet: str | None
    language: str | None
    raw: dict | None = None
```

Respect reasonable request intervals and source limits. Do not aggressively scrape websites. Prefer RSS and documented/public endpoints.

---

## 8. Filtering and Analysis Flow

Each monitoring cycle:

1. Load latest config from local config file.
2. For each enabled topic:
   - Fetch articles from enabled sources.
   - Normalize URLs.
   - Remove duplicates.
   - Filter old articles.
   - Apply keyword/phrase prefilter.
   - Skip already-processed articles in SQLite.
   - Build a small candidate batch for LLM.
3. Call LLM only for candidate articles.
4. Require LLM to return valid JSON.
5. Validate JSON schema.
6. If relevance score >= topic threshold and alert cooldown allows it:
   - save alert to SQLite
   - send notification through enabled notifiers
   - update UI status
7. Log errors but do not crash.

Do not call the LLM for every raw article. Keep costs low.

---

## 9. LLM Requirements

Use an OpenAI-compatible chat completion API by default. The base URL, model, API key, temperature, max tokens, and timeout must be configurable.

The app should be compatible with any OpenAI-compatible endpoint where practical.

The LLM must receive:

- the user topic prompt
- topic keywords
- related stock/watchlist candidates
- article title/snippet/source/published time/link
- strict instruction not to fabricate facts
- strict instruction to only base conclusions on provided article content and links
- strict instruction to include uncertainty if information is incomplete

The LLM must output strict JSON.

Desired JSON schema:

```json
{
  "relevance_score": 0,
  "is_actionable_alert": false,
  "event_type": "",
  "summary": "",
  "why_it_matters": "",
  "market_watch_suggestions": [
    {
      "ticker": "",
      "name_or_theme": "",
      "possible_direction": "bullish|bearish|mixed|unclear",
      "reason": "",
      "confidence": "low|medium|high"
    }
  ],
  "bullish_path": "",
  "bearish_path": "",
  "risk_notes": "",
  "uncertainty_notes": "",
  "source_reliability": "low|medium|high",
  "recommended_user_action": "watch_only|research_further|urgent_review|ignore",
  "notification_title": ""
}
```

Important: The app can call these “suggestions” or “market-watch suggestions”, not personalized financial advice. Include a brief disclaimer in notifications:

> This is AI-generated market monitoring, not financial advice. Verify sources before trading.

If the LLM returns invalid JSON, retry once with a repair prompt. If still invalid, log and skip the alert.

---

## 10. Notification Requirements

Implement a base notifier interface:

```python
class Notifier:
    name: str
    def send(self, alert: Alert) -> NotificationResult:
        ...
```

### Email notifier

Use SMTP.

Requirements:

- support TLS
- support multiple recipients
- subject includes relevance score and topic name
- plain text email is required
- HTML email is optional
- handle login/network errors cleanly
- never log password

Email content must include:

- topic name
- relevance score
- article title
- source
- published time
- original link(s)
- LLM summary
- why it matters
- market-watch suggestions
- bullish path
- bearish path
- risk notes
- uncertainty notes
- disclaimer

### WeCom notifier

Send markdown/text via webhook POST.

### Telegram notifier

Send message via Telegram Bot API.

### Generic webhook notifier

Support custom POST requests for arbitrary receiving APIs.

Configurable:

- URL via env var
- method, default POST
- headers
- JSON body template

Provide a safe default JSON payload:

```json
{
  "title": "...",
  "topic": "...",
  "relevance_score": 91,
  "summary": "...",
  "links": ["..."]
}
```

---

## 11. Database and Deduplication

Use SQLite.

Suggested tables:

```sql
articles(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT,
  normalized_url TEXT,
  title TEXT,
  title_hash TEXT,
  source TEXT,
  published_at TEXT,
  first_seen_at TEXT,
  last_seen_at TEXT,
  topic_name TEXT,
  processed INTEGER DEFAULT 0,
  UNIQUE(normalized_url, topic_name)
);

alerts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_name TEXT,
  article_url TEXT,
  title TEXT,
  relevance_score INTEGER,
  summary TEXT,
  llm_json TEXT,
  sent_at TEXT
);

notification_results(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  alert_id INTEGER,
  notifier_name TEXT,
  success INTEGER,
  error_message TEXT,
  sent_at TEXT
);
```

Deduplicate by:

- normalized URL
- title hash fallback
- source + title + published date fallback

Use a configurable dedupe window, default 72 hours.

---

## 12. Reliability Requirements

The app must be stable for long-running use.

Implement:

- network timeouts
- retries with limited exponential backoff
- source-specific error handling
- LLM timeout handling
- notification error handling
- no crashes on malformed RSS entries
- no UI freezing
- clear error messages in UI logs
- graceful shutdown
- safe stop/pause/resume behavior
- config validation before saving
- test notification buttons
- test LLM button

The app should continue monitoring other sources/topics even if one source fails.

---

## 13. Logging Requirements

Create logs:

```text
logs/app.log
logs/error.log
logs/alerts.log
```

Logs must include:

- startup and shutdown
- config loaded
- source fetch started/completed
- number of articles fetched
- number after filtering
- LLM calls started/completed
- alerts sent
- notification failures
- exceptions

Never log secrets.

---

## 14. Packaging and Deployment

Make the project easy to run in development:

```bash
python -m venv .venv
pip install -r requirements.txt
python main.py
```

Make it easy to build locally:

Windows:

```powershell
./scripts/build_windows.ps1
```

macOS:

```bash
./scripts/build_macos.sh
```

Use PyInstaller to generate distributable apps:

- Windows: `AI-News-Monitor-Windows.zip`
- macOS: `AI-News-Monitor-macOS.zip`

The packaged app should include:

- executable/app
- `config.example.yaml`
- `.env.example`
- README quick-start

It should not include real `.env`, real `config.yaml`, local logs, or SQLite database files.

---

## 15. GitHub Actions

Create `.github/workflows/build-release.yml`.

It should:

1. Run on push and pull request for tests.
2. Build release artifacts when a tag like `v*` is pushed.
3. Use matrix builds for:
   - `windows-latest`
   - `macos-latest`
4. Install Python.
5. Install dependencies.
6. Run tests.
7. Build PyInstaller artifact.
8. Upload artifacts.

Keep workflow simple and maintainable.

---

## 16. README Requirements

Write a clear README with:

1. What the app does
2. What it does not do
3. Security warning: never commit `.env` or `config.yaml`
4. Quick start for normal users
5. How to configure LLM API
6. How to configure Email
7. How to configure WeCom
8. How to configure Telegram
9. How to configure Generic Webhook
10. How to create/edit monitoring prompts
11. How to pause/resume/stop
12. How to run in development
13. How to build Windows/macOS packages
14. Troubleshooting
15. Future roadmap

README should be understandable to non-programmers.

---

## 17. Testing Requirements

Add pytest tests for:

- config loading and validation
- env var secret loading
- URL normalization
- deduplication
- LLM JSON schema validation
- notifier payload formatting
- email payload formatting without actually sending email
- source adapter parsing with mocked responses
- monitor loop logic using mocks

Network tests should be mocked. Do not require real API keys to run tests.

---

## 18. Acceptance Criteria

The project is complete when:

1. App launches on Windows/macOS in development mode.
2. UI is modern, minimal, and responsive.
3. User can input LLM settings and test them.
4. User can input Email settings and send a test email.
5. User can optionally input WeCom, Telegram, and generic webhook settings and test them.
6. User can create/edit/delete/pause/resume prompts/topics in the UI.
7. Monitoring can start, pause, resume, and stop.
8. App fetches free public news sources.
9. App filters articles using keywords.
10. App calls the LLM only for candidate articles.
11. App validates LLM JSON output.
12. App sends alerts with links, summary, suggestions, and risk notes.
13. App stores processed items in SQLite and avoids duplicate alerts.
14. App logs useful status/errors without logging secrets.
15. App can be packaged with PyInstaller.
16. GitHub Actions can run tests and build release artifacts.
17. The repository is safe to upload to GitHub with no secrets.
18. README explains setup clearly.

---

## 19. Important Implementation Notes

- Prioritize reliability and clean code over fancy UI animations.
- Keep the first version lightweight.
- Do not over-engineer the MVP.
- Avoid dependencies that make packaging difficult unless necessary.
- Prefer simple, explicit code.
- Avoid global mutable state where possible.
- Use typed dataclasses or pydantic if helpful, but do not add pydantic unless it materially improves validation.
- Keep UI and monitoring logic separated.
- Make notifiers and news sources easy to extend later.
- Use dependency injection or simple interfaces so tests can mock sources, LLM, and notifiers.
- Add comments where business logic is non-obvious.

---

## 20. First Topic Example

Include this default example topic only in `config.example.yaml`, not hardcoded in code:

```yaml
- name: "Trump Taiwan business cooperation"
  enabled: true
  output_language: "zh-CN"
  min_relevance_score: 80
  cooldown_minutes: 30
  prompt: >
    Monitor whether Trump visits Taiwan or announces concrete commercial,
    semiconductor, defense, AI, chip supply-chain, manufacturing, or trade
    cooperation with Taiwan. Only alert if the news is recent, concrete,
    market-relevant, and supported by at least one source link. Summarize the
    event, explain why it matters, suggest related watchlist stocks, and give
    both bullish and bearish risk paths. Output in Simplified Chinese.
  keywords:
    - "Trump Taiwan"
    - "Trump visits Taiwan"
    - "US Taiwan semiconductor cooperation"
    - "Taiwan defense deal"
    - "TSMC Nvidia"
    - "Taiwan trade deal"
    - "特朗普 台湾"
    - "台湾 半导体 合作"
  related_stocks:
    - "TSM"
    - "NVDA"
    - "ASML"
    - "AMAT"
    - "LRCX"
    - "KLAC"
    - "EWT"
    - "LMT"
    - "RTX"
  official_rss_urls: []
```

---

## 21. Final Instruction to Codex

Implement the project now. Create the complete repository structure, source code, config examples, tests, build scripts, GitHub Actions workflow, and README.

After implementation, run tests if the environment allows. If packaging cannot be fully executed in the current environment, still create the scripts and GitHub Actions workflow and explain exactly how to build on Windows/macOS.

Do not ask follow-up questions unless a requirement is technically impossible. Make reasonable engineering decisions and document them in the README.

---

## 02. Next-phase product prompt

Source file before consolidation: `02-codex_next_phase_prompt.md`

This file contains the high‑level specification for the **AI News Monitor – Next Phase** project.  The goal is to evolve the existing news monitor into a lightweight yet powerful tool that can gather real‑time information from around the globe, filter it intelligently, and deliver it to the user through email or messaging apps.  Analysis remains the user’s responsibility; the monitor focuses on timely collection and high‑quality surfacing of relevant articles.

## Purpose

Transform the existing AI‑powered news monitor into a **24/7 global information agent** that:

* Continuously fetches articles from a wide array of instantaneous news sources around the world and matches them against user‑provided prompts or keywords.
* Prioritises **quality over quantity** through robust relevance ranking, deduplication and source reliability scoring.  Information volume may be large, but only the most pertinent articles should be forwarded.
* Supports **bias awareness** by comparing multiple sources covering the same event and highlighting differences in tone or ownership.  Where possible, provide a short note about source bias or context without making editorial judgements.
* Offers **multilingual support** by translating and summarising non‑English articles (initially Chinese ↔ English) so that users receive coherent content regardless of source language.
* Delivers notifications instantly via **email and optional chat channels** (WeCom/Telegram).  Users can edit where the alerts go and adjust parameters at runtime through the configuration UI.
* Runs primarily as a **self‑hosted server** on the user’s computer for local processing and privacy.  Deployment should be simple: unzip and run the binary on Windows or macOS; no container orchestration required for everyday use.
* Presents a **modern, Apple‑style minimalist UI** that is fast, uncluttered and stylish, using generous whitespace, clean typography and a restrained colour palette.  Interface elements must not block content and should load quickly.

## Key Features and Requirements

1. **Advanced Filtering & Prioritisation** (adopt suggestion 1)
   * Implement a relevance scoring system that considers keyword matches, publication time, source reliability and recency.  Rank articles before delivery to keep only the most relevant.
   * Provide an adjustable threshold in the configuration UI so users can choose how strict the filter is.  Offer sensible defaults.

2. **Cross‑Source & Bias Analysis** (adopt suggestion 2)
   * For a given news event, gather reports from multiple sources and group them.  Use heuristics or AI to detect when stories refer to the same event.
   * Generate a short comparative summary that highlights differing viewpoints and notes potential bias or ownership context.  Present this alongside links to the original articles.
   * Allow the user to enable/disable bias analysis and choose whether to see only the best single source or a cluster of sources.

3. **Multilingual Translation & Summarisation** (adopt suggestion 4)
   * Integrate translation for languages not matching the user’s preferred language (default to Chinese and English).  Translate titles and summaries while preserving the original text.
   * Use the same LLM for summarising the translated content into 1–2 sentences.  Do not perform deeper analysis; simply condense and translate.
   * Allow the user to configure which languages to translate and the target language.

4. **Real‑Time Updates via SSE/WebSockets** (adopt suggestion 5)
   * Implement a server‑sent events (SSE) or WebSocket mechanism in the desktop app.  When new articles arrive or are enriched, push them to the UI without requiring a page reload.
   * Add a “live” banner or notification indicator in the UI when new items appear.
   * Ensure the local server remains efficient even with persistent connections.

5. **Technical & Deployment Optimisation** (adopt suggestion 12)
   * Audit the codebase to eliminate unnecessary dependencies and reduce memory footprint.  Remove unused functions, avoid artificial delays and profile the critical paths.
   * Package the application with PyInstaller for both Windows and macOS.  Create a standalone binary that includes all required libraries and a minimal Python runtime.
   * Update GitHub Actions workflows to build these binaries automatically.  Supply `.env.example` and `config.example.yaml` files for easy configuration.  Ensure `.env`, `config.yaml`, `logs` and `data` directories are excluded from version control.
   * Avoid hard‑coding any API keys, email addresses or chat tokens.  All secrets must be loaded from environment variables or through the configuration UI.

6. **Language Support and Unified Output**
   * The application must recognise **Chinese and English** input sources only.  Do not monitor or translate articles from other languages.  Users may enter prompts in either Chinese or English; the monitor must handle both natively.
   * Provide a **global language toggle** (Chinese ↔ English) that affects the entire application at both the system and scripting levels.  Selecting a language must immediately update the UI, all logs, summaries and notifications without restarting.  When a language is selected, ensure that every piece of output—including article summaries, error messages, configuration labels and help text—is presented **consistently** in that language.
   * Offer a simple switch in the settings panel for users to choose their preferred language.  The toggle should be clearly labelled in both languages (e.g. “语言 / Language”) so that switching from one to the other is intuitive.  The default can follow the system locale.

7. **Expanded Chat Notifiers**
   * Beyond the existing email, WeCom and Telegram channels, **add support for ordinary WeChat and QQ** where feasible.  If there is no official API for direct push, integrate via trusted third‑party relay services (such as Server酱、ServerChan 或 Chanify) that forward notifications into personal WeChat/QQ accounts.  Provide clear setup instructions, warn about any reliability or privacy trade‑offs and allow the user to enable/disable this feature.
   * **Restructure the notifications settings UI** to emphasise clarity and reduce cognitive load: break the page into separate sections for each channel (Email, WeCom, Telegram, WeChat, QQ, Webhook, etc.).  Within each section, show only the minimum required fields (e.g. address, token, webhook URL) and hide advanced options behind an “Advanced” toggle.  Use descriptive labels in the selected language.
   * Add form validation so that channels cannot be enabled until required fields are completed.  Display real‑time feedback on whether the system can connect to each service (Connected / Error / Disconnected) along with the last successful message time, so users can assess **long‑term stability**.

8. **Natural Animations and Modern Dialogs**
   * Enhance the UI with subtle, non‑intrusive animations: e.g. fade transitions when changing pages, smooth expansion/collapse of configuration panels and gentle notifications when new articles arrive.  Animations must never block user actions or slow down the interface.
   * Use modern dialog components for confirmation, errors and status messages.  Dialogs should match the minimalist theme and support both Chinese and English text.
   * Ensure that all interaction elements (buttons, toggles, forms) are keyboard navigable and accessible.

9. **Port and Service Stability**
   * Design the notification and API endpoints (SMTP, WeCom/Telegram/WeChat/QQ webhooks, translation services) to handle reconnections and failures gracefully.  Implement retry logic with exponential backoff when sending notifications or making API calls.
   * Expose health checks for each external service so that the server can report whether a channel is currently operational.  Display this information in the configuration UI and log persistent failures.

10. **Minimalist UI & Local Control**
   * **Rebuild the interface** in the spirit of Apple design: large headings, generous whitespace, crisp sans‑serif fonts and a restrained colour palette with a single accent colour.  Keep the aesthetic lightweight and modern, avoid overcrowding or unnecessary decoration.
   * Ensure the layout is responsive and comfortable on desktops and laptops (primary target environment).  Components must load quickly, react to user input without lag and avoid heavy animations that slow down weaker machines.
   * Provide a **comprehensive dashboard** where the user can monitor the system’s status: total articles processed, last fetch time, queue length, connection health for each notifier, and log messages.  Users should be able to **pause, resume and stop** the monitoring process, and view immediate feedback on their actions.
   * Create intuitive **configuration panels** that allow users to:
     * View and edit where information is sent (email addresses, chat accounts).  Adding or removing channels should be as simple as filling out a short form.
     * Input or update API keys for the LLM and translation services, and choose which model or translation engine to use.
     * Define or modify keywords, prompts and other monitoring parameters without editing files by hand.
     * Adjust the relevance threshold, select which languages to translate, enable/disable bias comparisons and specify how often to refresh sources.
   * Provide bilingual interface text (Chinese and English) across all views, ensuring that changing the language toggle updates the entire UI, including all control labels, help text and error messages.
   * Show complete feedback for each operation (e.g. when a new article is matched, display summary, source, and processing time) and allow the server operator to view raw logs if deeper debugging is needed.

11. **Global Source Integration & Quality Assurance**
   * Expand the list of news sources beyond the current defaults (GDELT, Google News RSS, Yahoo Finance).  Use additional free APIs or public RSS/Atom feeds to increase coverage.  Maintain a curated list of reliable sources and allow users to add custom feeds via the UI.
   * Deduplicate articles across sources using URL, title similarity and content fingerprinting.  Ensure that duplicates from different sources are not sent multiple times.
   * Fetch metadata for each source (language, reliability score).  Use reliability scores to down‑rank or exclude low‑trust outlets.

12. **Easy Deployment & Operation**
   * Default running mode should be as a local server that starts when the user launches the binary.  Provide a system tray icon or status indicator.
   * Users should access the UI via a local browser at `http://localhost:PORT`.  Optionally allow remote access via LAN with proper security and authentication.
   * For those deploying on a remote VPS, provide a simple set‑up guide: install dependencies, configure environment, run the binary or container.

## Implementation Steps

1. **Planning & Analysis**
   * Review the existing codebase to understand the current architecture, data flow and dependencies.
   * Identify modules that need expansion (e.g. source fetchers, notifier engines, UI components).

2. **Source Expansion & Ranking**
   * Create new fetcher classes for additional RSS/Atom feeds and public news APIs.
   * Implement deduplication and reliability scoring for each fetched article.  Provide a function to compute a combined relevance score.

3. **Bias Analysis Module**
   * Develop a grouping algorithm to cluster articles referring to the same event using title similarity or entity extraction.
   * For each cluster, generate a short comparative summary (use LLM or templated heuristics).  Annotate sources with ownership or known bias when available.

4. **Translation & Summarisation**
   * Integrate a translation service (e.g. OpenAI, HuggingFace translation models) to translate titles and summaries into the user’s preferred language.  Preserve original text for reference.
   * Use the existing LLM client to summarise translated content.  Ensure both translation and summary are optional and configurable.

5. **Real‑Time Delivery & UI Enhancements**
   * Implement SSE/WebSocket endpoints on the backend.  Update the frontend to open a persistent connection and append new articles to the list as they arrive.
   * Add UI controls to adjust real‑time update preferences (e.g. enable/disable, update frequency).
   * Apply the minimalist design guidelines throughout the interface.  Replace heavy components with lightweight alternatives; remove unused icons or animations.

6. **Configuration & Secrets Handling**
   * Extend the configuration schema to include new settings: relevance threshold, languages, bias analysis toggle, additional sources.
   * Build forms in the UI for editing configuration.  Save changes to `config.yaml` or another persistent store.  Do not require a restart to apply most changes.
   * Ensure all secrets are stored only in `.env` or via the UI’s secret input fields.  Never commit sensitive data to the repository.

7. **Testing & Packaging**
   * Write unit tests for new modules: source deduplication, relevance scoring, bias grouping, translation pipeline and SSE handler.
   * Use continuous integration to run tests on each commit.
   * Update packaging scripts to include the new dependencies.  Test that the built binaries run on Windows 10/11 and macOS (Intel & M‑series).
   * Provide an updated `README.md` detailing the new features, configuration options, installation steps and usage instructions.

## Completion Criteria

The Codex agent should consider this implementation complete when:

* All new modules and UI elements described above are present and functional.
* The application can fetch articles from multiple global sources, deduplicate them, rank them by relevance and deliver notifications in real time.
* Multilingual translation and bias comparisons work as expected, and users can toggle these features.
* The UI adopts the minimalist design, and users can configure sources, destinations, API keys and parameters on the fly.
* Packaging scripts produce working binaries for both Windows and macOS, with `.env.example` and `config.example.yaml` provided.
* Automated tests pass and no secrets are hard‑coded in the codebase.

---

## 03. Update prompt

Source file before consolidation: `03-codex_update_prompt.md`

The purpose of this update is to refine and enhance the AI News Monitor desktop application you already started building.  The new requirements focus on usability, aesthetics, configuration defaults and extensibility, while preserving the project's core philosophy of being lightweight, secure and easily deployable on Windows and macOS.

## Key objectives

1. **Default configuration presets** – In the current UI the API configuration pages (LLM and notifier APIs) ask users to pick every parameter (e.g. temperature, top‑p, presence penalty for LLM; mail host, port, encryption etc. for SMTP).  Add a **recommended default configuration** option for each API type.  When a user chooses the recommended preset, sensible defaults are applied automatically and they only need to enter the mandatory fields (LLM model name and API key; email address and password; chat webhook etc.).  Keep the existing full customisation option so advanced users can fine‑tune.

2. **Modern, Apple‑style minimalist UI** – The current UI is efficient but visually dated.  Redesign it using minimalist principles: reduce visual clutter, emphasise simplicity and clarity, and employ generous whitespace【950642291841969†L85-L103】.  Use a clean sans‑serif typeface and avoid decorative fonts; clear typography helps users focus on content【950642291841969†L116-L123】.  Limit the colour palette to a few neutral and harmonious colours to create a calm, balanced atmosphere【950642291841969†L125-L134】, and use occasional high‑contrast accent colours only to highlight actionable elements such as buttons【950642291841969†L137-L141】.  Implement smooth, non‑distracting transitions between screens.  Maintain the high performance of the app: minimalism should lead to faster load times by reducing unnecessary elements【950642291841969†L155-L158】.  The UI must remain bug‑free and extremely low‑latency.

3. **Customisable news sources** – Currently the news monitor has a fixed set of websites.  Introduce a configuration panel where users can view, add and remove news sources.  You should preserve the pre‑configured sources delivered in the existing version.  When a user adds a new source, only ask for the minimum necessary data (e.g. a website name and an RSS/Atom feed URL).  Validate the input and show a short description of what constitutes an acceptable source: for example, news sites with publicly accessible RSS/Atom feeds or free news APIs.  Warn users against adding unauthorised or paywalled sources.  Save the sources list in the same configuration system used for other settings.

4. **Code quality and performance audit** – Review the existing codebase and remove any redundant functions or artificial delays.  Ensure there are no hidden bugs.  Refactor modules where necessary to improve maintainability.  Run the full test suite and measure performance; minimalism should not introduce regressions.  Leave the project structure ready for future expansions and versioning.

5. **Maintain previous requirements** – Continue enforcing the original design decisions: no secrets hard‑coded in the repository; all API keys, emails and webhooks must be loaded from local environment files or through the configuration UI.  Preserve the multi‑notifier system (Email default, optional WeCom/Telegram/Generic webhook) and ensure users can start, pause, resume and stop the monitor at any time.  Keep the configuration file (`config.yaml`) and `.env` pattern for secrets.  The program must still be packaged for Windows and macOS via PyInstaller with GitHub Actions, with a `config.example.yaml` and `.env.example` included.

## Implementation steps

1. **Analyse existing project** – Before coding, scan the project to understand how the current configuration pages, UI components and news fetchers are implemented.  Identify where to hook the new default preset logic and where to add the news sources panel.

2. **Add default presets** – For the LLM settings create a set of default parameters (e.g. temperature=0.7, top_p=1.0, max_tokens=1024).  For each notifier type define recommended SMTP settings or default headers.  In the configuration UI, provide a toggle/drop‑down to choose between “Recommended defaults” and “Custom settings”.  Update the configuration schema to store the preset choice and only persist optional parameters when the user overrides the default.

3. **Refactor the UI** – Switch to a minimalist design library or customise the existing components to follow the minimalist rules.  Increase white space around sections and use consistent spacing.  Set the font to a clean sans‑serif family (e.g. `Inter`, `SF Pro`, or system default).  Restrict the colour palette to neutral backgrounds with subtle accent colours for buttons, emphasising functionality rather than decoration.  Apply smooth transitions for screen changes, but ensure animations are lightweight.  Test that the app remains responsive and loads quickly; minimalism should reduce cognitive load and improve readability【950642291841969†L87-L101】.

4. **News sources management** – Add a section in the settings page (or a separate page) that lists the current news sources.  Each entry should display the name and endpoint (RSS/Atom feed URL).  Provide buttons to add or remove sources.  When adding, ask for the site name and feed URL; validate the URL and refuse duplicates.  Document what types of sources are supported (public feeds and APIs) and caution users against paywalled or scraped sites.  Store the sources list in the user’s configuration file.

5. **Audit and optimise** – Run the unit tests and fix any failing ones.  Profile the app to identify bottlenecks.  Eliminate unused imports and functions.  Verify that the UI changes do not introduce errors.  Confirm that startup times and memory usage meet the original performance goals.

6. **Update documentation** – Extend `README.md` to describe the new default preset option, the minimalist UI, and how to manage news sources.  Update the configuration examples.  Add notes about recommended fonts and colour palettes inspired by Apple‑style minimalism.  Provide guidance on selecting credible news sources.

7. **Release preparation** – Update the packaging scripts to ensure all new dependencies are included.  Add tests for the default preset logic and the news source manager.  Once tests pass, modify the GitHub Actions workflow if necessary to build the updated binary for Windows and macOS.  Ensure that `.env`, `config.yaml`, `data/`, and `logs/` remain ignored by git.

At completion, the project should provide a modern, minimalistic interface with configurable defaults and sources, remain secure and performant, and be ready for future iterations.

---

## 04. Next-iteration prompt

Source file before consolidation: `04-ai_news_monitor_next_iteration_prompt.md`

# AI News Monitor — Next Iteration Codex Goal Prompt

## How to use this file

Put this file in the root of the current AI News Monitor repository. Then run Codex CLI from the project root and start the task with:

```text
/goal Read ./ai_news_monitor_next_iteration_prompt.md carefully and implement everything described in it. Treat this file as the authoritative next-iteration product and engineering specification. Before coding, read HANDOFF.md, README.md, config.example.yaml, and tests/test_next_phase_features.py. Work in focused milestones, run tests after each milestone, avoid hard-coding secrets, and finish with a requirement-by-requirement audit.
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

---

## 05. Final target candidate prompt

Source file before consolidation: `05-ai_news_monitor_final_target_candidate_prompt.md`

# AI News Monitor v0.9 — Final Target Candidate + Open Source Release Readiness

## Recommended Codex CLI command

Place this file in the repository root, then run Codex CLI from the repository root and use:

```text
/goal Read ./ai_news_monitor_final_target_candidate_prompt.md carefully and implement everything described in it. Treat this file as the authoritative product and engineering specification for the next major iteration. Before coding, read HANDOFF.md, README.md, SOURCE_GUIDE.md, NOTIFICATION_GUIDE.md, config.example.yaml, src/, and tests/. Do not assume real API keys or real run data. Work in milestones, run tests after each milestone, avoid hard-coded secrets, keep all source code English-only, prepare the repository for public open-source release under GPL-3.0-only, and finish with a requirement-by-requirement audit.
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

---

## 06. Pre-GitHub interface stabilization prompt

Source file before consolidation: `06-ai_news_monitor_pre_github_interface_stabilization_prompt.md`

# AI News Monitor — Pre-GitHub Release Interface Stabilization Prompt

## Recommended Codex CLI command

Place this file in the repository root, then run Codex CLI from the repository root:

```text
/goal Read ./ai_news_monitor_pre_github_interface_stabilization_prompt.md carefully and implement everything described in it. Treat this file as the authoritative pre-GitHub release stabilization specification. Before coding, read HANDOFF.md, README.md, README.zh-CN.md, SOURCE_GUIDE.md, NOTIFICATION_GUIDE.md, config.example.yaml, src/, tests/, locales/, and .github/workflows/. Do not assume real API keys, real Gmail credentials, real webhook tokens, or real runtime data. Focus on interface stability, actionable diagnostics, beginner-friendly setup, UI readability, lightweight implementation, and public GitHub release readiness. Keep source code English-only, keep Chinese only in locale/documentation resources, run tests after each milestone, and finish with a requirement-by-requirement audit.
```

---

## Background

The current project has reached a strong release-candidate stage, but real user testing revealed important release blockers:

1. The user entered the LLM API information correctly, but the **LLM test failed**.
2. The user entered Gmail SMTP information correctly, but the **Email test failed**.
3. Therefore, before publishing to GitHub, the project must re-check the **stability and feasibility of every external interface**, not only LLM and Gmail.
4. The UI has a readability problem: the top module/header background colour and font colour are too similar.
5. The overall font style is not modern enough. Use an Apple-like system font stack, but do not bundle proprietary Apple font files.
6. User guidance is insufficient. For every field the user must fill, the app must clearly show:
   - Which fields are required.
   - What each field means.
   - Where to obtain the value.
   - How to test it.
   - What common failures mean.
7. The app should remain complete, feasible, lightweight, and ready to publish as an open-source GitHub repository.

This iteration is not a feature-expansion sprint. It is a **pre-GitHub release stabilization and usability pass**.

---

# Non-negotiable rules

## 1. Do not assume real secrets

Do not add, request, store, or commit real credentials.

No real:

- API keys
- Gmail app passwords
- SMTP passwords
- Webhook URLs
- Telegram tokens
- WeCom keys
- ServerChan/Chanify/Qmsg keys
- Personal emails
- Chat IDs

Tests must use mocks, dummy placeholders, local fake servers, or monkeypatching.

## 2. Source code must remain English-only

All source code must remain English-only.

This applies to:

- Python files
- Tests
- Scripts
- GitHub Actions
- Embedded HTML templates
- Embedded CSS/QSS
- JavaScript if any
- Comments
- Docstrings
- Log templates
- Error templates
- UI string keys in code

Chinese is allowed only in:

- `locales/zh-CN.*`
- `README.zh-CN.md`
- Chinese documentation resources

Do not hard-code Chinese UI strings in source code. Use i18n keys.

## 3. Keep the project lightweight

Avoid heavy new dependencies. Prefer:

- Existing app architecture
- Existing PySide/browser local UI approach
- Small diagnostics modules
- Mockable interfaces
- Lightweight HTML/CSS/JS
- Existing test stack

Do not add a large frontend framework unless absolutely necessary and justified.

## 4. Do not bundle proprietary fonts

Use Apple-like system font stacks only.

For browser UI:

```css
font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
```

For PySide UI:

- Use system fonts or generic sans-serif fallbacks.
- Do not include Apple font files.
- Do not distribute proprietary font assets.

---

# Main goal

Before public GitHub release, make the app genuinely usable by improving:

1. LLM API diagnostics and compatibility.
2. Gmail/SMTP diagnostics and setup clarity.
3. Stability checks for all external interfaces.
4. Required-field guidance and helper links.
5. UI contrast, readability, typography, and layout.
6. Test coverage for interface diagnostics.
7. GitHub release readiness.

---

# Workstream A — External Interface Stability Audit

## Objective

Every external interface must have a reliable, testable, user-readable health check.

Audit and improve these interfaces:

- OpenAI-compatible LLM API
- LLM translation/summarization
- Gmail/SMTP email
- Telegram
- WeCom
- WeChat Relay
- QQ Relay
- Generic Webhook
- GDELT
- Google News RSS
- Yahoo Finance RSS
- Public RSS/Atom
- Official RSS/Atom
- Source Library feeds
- Custom RSS/Atom sources
- Local browser server endpoints
- SSE/WebSocket real-time stream

## Required diagnostics fields

For every interface, expose:

- Configured / Not configured
- Enabled / Disabled
- Required fields missing
- Last test time
- Last success time
- Last failure time
- Last error category
- Redacted technical error detail
- User-facing suggested fix
- Test button
- Help link

## Standard error categories

Normalize low-level exceptions into useful categories:

```text
missing_required_field
invalid_url
invalid_email_address
invalid_api_key
model_not_found
unsupported_model_api
base_url_unreachable
api_auth_failed
api_rate_limited
api_timeout
tls_or_certificate_error
network_unreachable
proxy_or_firewall_issue
smtp_auth_failed
smtp_starttls_failed
smtp_sender_rejected
smtp_recipient_rejected
smtp_connection_timeout
smtp_provider_blocked
webhook_unreachable
webhook_http_error
webhook_auth_failed
feed_unreachable
feed_parse_failed
feed_empty
source_language_unsupported
local_server_port_in_use
sse_connection_failed
unknown_error
```

## Acceptance criteria

- No interface test simply says "failed".
- Every failure gives a category, explanation, and suggested fix.
- Secrets are redacted in all UI/log/test output.
- Tests cover diagnostic classification with mocks.

---

# Workstream B — LLM API Compatibility and Diagnostics

## Current user problem

The user correctly entered LLM API information, but the LLM test failed.

The app must make the LLM setup robust enough to tell whether the failure is caused by:

- Missing key
- Invalid key
- Wrong base URL
- Network/proxy/firewall issue
- Model ID unavailable
- Wrong API endpoint/payload for the selected model
- Rate limit
- Timeout
- Unsupported provider behaviour

## Required fields

Clearly mark these required fields:

- Provider
- Base URL
- Model ID
- API key

Recommended default values:

```yaml
provider: openai_compatible
base_url: https://api.openai.com/v1
api_key_env: LLM_API_KEY
preset: recommended
```

Do not hard-code only one model as valid. The model ID must remain user-editable.

## Model compatibility

The app must not assume all models support the same endpoint style.

Add or improve support for:

- OpenAI-compatible models endpoint check where available.
- Minimal model availability check.
- Minimal generation request using the current client.
- Clear detection when the selected model is not supported by the app's current request format.

If the app currently uses only Chat Completions, verify whether the selected model works with that endpoint. If not, provide actionable feedback and, if practical, add support for the provider's required endpoint style.

Do not guess silently. Tell the user exactly what failed.

## LLM settings UI

The LLM settings card must include:

- Required badges.
- API key field with masking.
- Base URL field.
- Model ID field.
- Provider field.
- Recommended preset.
- Advanced parameters hidden by default.
- "Get API key" helper link.
- "What is Base URL?" helper.
- "What is Model ID?" helper.
- "Test LLM connection" button.
- "Fetch available models" button if feasible.
- Test result panel showing:
  - Success/failure
  - Tested model
  - Latency
  - Error category
  - Suggested fix

## Example user-facing messages

These messages must be stored in i18n resources, not hard-coded Chinese in source code.

### Invalid API key

```text
Authentication failed. The API key was rejected. Create a new API key, paste it again, and make sure there are no extra spaces.
```

### Model not found

```text
Model not found. The model ID may be unavailable for your account. Check the exact model name in your provider dashboard or use "Fetch available models".
```

### Unsupported endpoint

```text
The model may not support the current API request format. Try another model or update the provider/API mode.
```

### Base URL unreachable

```text
The base URL could not be reached. Check the URL, network connection, VPN/proxy, firewall, or DNS settings.
```

### Rate limit

```text
The provider returned a rate limit error. Wait and try again, or use a lower-frequency monitoring interval.
```

## Tests

Add tests using mock HTTP clients or monkeypatching for:

- Missing API key
- Invalid API key / 401
- Model not found / 404
- Rate limit / 429
- Timeout
- Base URL unreachable
- Unsupported endpoint/payload
- Valid minimal response
- Secret masking
- Fetch available models, if implemented

Automated tests must not call real LLM APIs.

---

# Workstream C — Gmail / SMTP Compatibility and Diagnostics

## Current user problem

The user correctly entered Gmail SMTP information, but the Email test failed.

The app must make Gmail setup clear, testable, and failure-explainable.

## Gmail required fields

For Gmail, required fields are:

```text
Enabled: on
SMTP Host: smtp.gmail.com
SMTP Port: 587
Encryption: STARTTLS
Username: sender Gmail address
Password: sender Gmail App Password
From Address: sender Gmail address
To Address: recipient email address
```

Important user guidance:

- Gmail password field means **Gmail App Password**, not normal Google login password.
- The app password belongs to the **sender Gmail account**.
- The receiver does not need an app password.
- `From Address` should usually match `Username`.

## Gmail preset

Add or improve a Gmail preset:

```text
Preset: Gmail
```

When selected, automatically fill:

```text
SMTP Host: smtp.gmail.com
SMTP Port: 587
Encryption: STARTTLS
```

Show only these fields by default:

- Username
- App Password
- From Address
- To Address

Hide advanced SMTP settings behind an Advanced toggle.

## Helper links

Add visible helper links/buttons:

- "How to create a Gmail App Password"
- "Open Google App Passwords"
- "Why can't I use my Gmail login password?"
- "Test Email"

Also explain:

- Sender vs receiver relationship.
- App password requirement.
- 2-Step Verification requirement.
- Work/school/organization Google accounts may disable app passwords.
- Network/firewall may block SMTP port 587.

## Email test flow

The test should:

1. Validate required fields locally.
2. Validate sender and receiver email syntax.
3. Warn if From Address differs from Username.
4. Attempt SMTP connection.
5. Start TLS if configured.
6. Authenticate.
7. Send a minimal test message.
8. Classify failure cause.
9. Display actionable fix.
10. Redact app password from all logs/UI.

## Example user-facing messages

Use i18n resources.

### SMTP auth failed

```text
Gmail rejected the login. Use a Gmail App Password for the sender account. Do not use your normal Google password. The sender account usually needs 2-Step Verification enabled.
```

### Sender rejected

```text
The From Address may not match the authenticated Gmail account. Try using the same Gmail address for Username and From Address.
```

### Recipient rejected

```text
The recipient address was rejected. Check the To Address for typos.
```

### STARTTLS failure

```text
STARTTLS failed. Check the encryption setting, SMTP host, port, and network environment.
```

### Timeout

```text
The SMTP server could not be reached. Check network, VPN/proxy, firewall, or whether port 587 is blocked.
```

## Tests

Use fake SMTP or monkeypatch `smtplib` to test:

- Missing required fields
- Invalid sender email
- Invalid recipient email
- STARTTLS failure
- Auth failure
- Sender rejected
- Recipient rejected
- Timeout
- Successful test email
- Secret masking

Automated tests must not use real Gmail.

---

# Workstream D — Notification Center Stability

## Objective

Make all notification channels understandable, testable, and reliable.

## Channels

Support existing channels:

- Email
- Telegram
- WeCom
- WeChat Relay
- QQ Relay
- Generic Webhook

## UI requirements

Create or improve a **Notification Center** with one card per channel.

Each card shows:

- Channel name
- Short description
- Configured / Not configured
- Enabled / Disabled
- Connected / Error / Disconnected
- Required fields completed
- Last success time
- Last failure time
- Failure count
- Last error category
- Last error message
- Fallback priority
- Test button
- Setup guide link
- Advanced settings collapsed by default

## Required field guidance per channel

Each channel must show:

- Required fields
- Where to get them
- Example values
- Test button
- Typical failure causes
- Privacy/stability notes

## WeChat and QQ

Do not claim stable native personal WeChat/QQ bot support.

Use relay wording:

```text
Personal WeChat/QQ do not provide a stable official bot API for this use case. This app supports relay services such as ServerChan, Chanify, Qmsg, or generic webhooks. Reliability depends on the relay provider. Configure Email or Telegram as a fallback.
```

## Retry and fallback

Preserve/improve:

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

1. Try primary channel.
2. Retry with exponential backoff if it fails.
3. Try fallback channels in order.
4. Record final result.
5. Show result in UI and logs.

## Tests

Add tests for:

- Required field validation per channel.
- Test result classification.
- Retry/backoff.
- Fallback routing.
- Secret masking.

---

# Workstream E — Source Interface Stability

## Objective

Make source fetching stable, transparent, and testable.

## Source cards should show

For each source:

- Enabled state
- Source type
- Language
- Category
- Reliability score
- Last test time
- Last fetch time
- Last success
- Last failure
- Consecutive failures
- Last error category
- Last error message
- Recent returned article count
- Test button
- Open website/help button

## Source test flow

For RSS/Atom:

1. Validate URL.
2. Fetch with timeout.
3. Parse feed.
4. Count entries.
5. Detect language if feasible.
6. Report success/empty/failure.

For API sources:

1. Validate required parameters.
2. Perform minimal test request.
3. Report success/failure.

## Bulk source test

Add a "Test enabled sources" action.

Report:

- Total tested
- Success count
- Failure count
- Empty feed count
- Unsupported language count
- Top failure reasons

## Tests

Add mock tests for:

- Valid RSS
- Invalid RSS
- Empty feed
- Timeout
- Invalid URL
- Unsupported language
- Bulk test summary
- Source health persistence

---

# Workstream F — UI Readability, Contrast, Typography, and Layout

## Current UI problems

- Header/top module colour and text colour are too similar.
- UI can feel glare-prone.
- Colours are too monotonous.
- Font style is not modern enough.
- Settings are too form-heavy.
- Required-field guidance is visually insufficient.
- Overall interaction is still too developer-oriented.

## Header/top navigation

Fix contrast immediately.

Requirements:

- Header background and text must have strong contrast.
- Active tab/section must be clearly distinct.
- Hover/selected states must be visible.
- Avoid grey-on-grey low contrast.
- Avoid light text on light background.

If practical, add a static style/contrast test or snapshot check.

## Typography

Use Apple-like system font stack.

Browser UI:

```css
font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
```

PySide UI:

- Use system/default sans-serif.
- Prefer clean modern fonts.
- Do not bundle font files.

## Visual design

Improve all pages:

- Lower-glare background.
- More modular cards.
- Less rigid form layout.
- Better whitespace.
- Better typography hierarchy.
- Softer neutral palette.
- Clear accent colour.
- Consistent inputs/buttons.
- Friendly status badges.
- Modern toasts/dialogs.
- Smooth but lightweight transitions.

## Settings page

Reorganize into clear cards:

- General
- Language
- LLM
- Alerts
- Sources
- Notifications
- Local Server
- Advanced

Each card includes:

- Short explanation
- Required fields
- Helper links
- Test buttons
- Advanced fields collapsed by default
- Save/apply feedback

## Acceptance criteria

- Header contrast problem is fixed.
- Font feels modern and Apple-like.
- UI is less glaring and less scattered.
- Settings are simpler and lower-barrier.
- The app stays lightweight and responsive.

---

# Workstream G — Required-Field Guidance

## Objective

Make setup possible for users without external help.

For every user-filled field, add:

1. Required/optional indicator.
2. Short explanation.
3. Example value.
4. Direct helper link.
5. Test/verify button if feasible.
6. Friendly failure message.
7. Advanced fields collapsed by default.

## Must cover

### LLM

- Provider
- API key
- Base URL
- Model ID
- Advanced generation parameters

### Email/Gmail

- SMTP host
- SMTP port
- Encryption
- Username
- Gmail App Password
- From address
- To address

### Telegram

- Bot token
- Chat ID

### WeCom

- Webhook URL

### WeChat Relay

- ServerChan/Chanify token or webhook URL

### QQ Relay

- Qmsg or generic relay settings

### Generic Webhook

- URL
- Method
- Headers if advanced

### Sources

- RSS/Atom URL
- Source language
- Reliability score
- Source category
- Source website

### Topics

- Prompt
- Keywords
- Alert mode
- Relevance threshold

## Acceptance criteria

- The user can configure the minimum viable app without asking ChatGPT what each field means.
- Required fields are visually obvious.
- Every required external credential/URL field tells the user where to get it.

---

# Workstream H — Public GitHub Readiness

## Objective

Prepare for public GitHub release.

## Required checks

Ensure these remain true:

- Source code English-only.
- README language switching works.
- `README.md` and `README.zh-CN.md` are current.
- GPL-3.0-only `LICENSE` exists.
- `AI_DISCLOSURE.md` exists.
- `CONTRIBUTING.md` exists.
- `SECURITY.md` exists.
- `CHANGELOG.md` exists.
- `SOURCE_GUIDE.md` exists.
- `NOTIFICATION_GUIDE.md` exists.
- `.env.example` exists.
- `config.example.yaml` parses.
- `.gitignore` excludes secrets/logs/data.
- No real secrets are committed.
- GitHub Actions exist for CI/build/release.

## Documentation updates

Update README and guides to include:

- LLM troubleshooting.
- Gmail App Password explanation.
- Email sender vs receiver explanation.
- Notification testing.
- Source testing.
- Diagnostics page.
- Common failure categories.
- What to do when a test fails.

---

# Workstream I — Tests and Manual Verification Checklist

## Automated tests

Add or improve tests for:

1. LLM diagnostics using mocked provider.
2. Gmail diagnostics using mocked `smtplib`.
3. Email required field validation.
4. Telegram required field validation.
5. WeCom required field validation.
6. WeChat/QQ relay required field validation.
7. Generic webhook validation.
8. Notification fallback and retry.
9. Source diagnostics.
10. Bulk source test summary.
11. Header/top navigation style/contrast if practical.
12. Apple-like font stack in browser CSS/templates if practical.
13. Required helper links exist for key fields.
14. No Chinese in source code.
15. README language switching.
16. GPL license exists.
17. AI disclosure exists.
18. Config example parses.
19. `.env.example` exists.
20. Secret masking.
21. Local server health/status endpoints.
22. SSE event emission.
23. Fast Alert formatting.
24. Full Analysis optional formatting.

## Manual release checklist

Create or update `docs/RELEASE_CHECKLIST.md` covering:

- Launch app.
- Open local console.
- Configure LLM with real user key.
- Test LLM and interpret diagnostics.
- Configure Gmail with app password.
- Test email and interpret diagnostics.
- Configure at least one fallback notifier.
- Test notifier fallback.
- Enable source packages.
- Test enabled sources.
- Create topic.
- Start monitoring.
- Confirm dashboard updates.
- Confirm alert formatting.
- Confirm logs do not reveal secrets.
- Confirm UI contrast/readability.
- Confirm macOS build.
- Confirm Windows GitHub Actions build.

---

# Final audit report

At the end, output:

```text
## Completed
- ...

## Partially completed
- ...

## Not completed / blocked
- ...

## Interface diagnostics implemented
- LLM:
- Gmail/SMTP:
- Telegram:
- WeCom:
- WeChat Relay:
- QQ Relay:
- Generic Webhook:
- Sources:
- Local server/SSE:

## UI/UX improvements
- ...

## Required-field guidance improvements
- ...

## Tests run
- ...

## Build / GitHub Actions status
- ...

## GitHub release readiness
- ...

## Remaining risks
- ...

## Recommended next step
- ...
```

---

# Definition of done

This iteration is complete only when:

- LLM test failures are actionable and classifiable.
- Gmail/SMTP test failures are actionable and classifiable.
- All notification/source interfaces have clear health/test paths.
- Required fields are obvious and well documented in UI.
- Helper links exist for user-obtained values.
- Header contrast issue is fixed.
- Typography uses Apple-like system font stack.
- UI is less glaring, less scattered, more modern, and still lightweight.
- Source code remains English-only.
- README English/Chinese switching remains intact.
- GitHub Actions remain present and functional.
- Automated tests pass in a proper environment.
- No secrets are committed or logged.
- The project is closer to public GitHub release.

---

## 07. Source reliability and freshness prompt

Source file before consolidation: `07-ai_news_monitor_source_reliability_freshness_prompt.md`

# AI News Monitor — Source Reliability, Freshness & Intelligence Gaps Upgrade Prompt

## Codex CLI command

Place this file in the repository root, then run Codex CLI from the repository root:

```text
/goal Read ./ai_news_monitor_source_reliability_freshness_prompt.md carefully and implement everything described in it. Treat this file as the authoritative specification for the next iteration. Before coding, read CHATBOT_CONTEXT.md, HANDOFF.md, README.md, README.zh-CN.md, SOURCE_GUIDE.md, NOTIFICATION_GUIDE.md, docs/RELEASE_CHECKLIST.md, config.example.yaml, src/, tests/, locales/, and .github/workflows/. Do not assume real API keys, real Gmail credentials, real webhook tokens, or real runtime data. Do not copy code, assets, data, or text from external projects. Only use architectural ideas. Focus on source reliability, freshness states, intelligence gaps, source caching, smart polling/backoff, and source-package presets while keeping the app lightweight and public-GitHub-ready. Keep source code English-only, keep Chinese only in locale/documentation resources, run tests after each milestone, and finish with a requirement-by-requirement audit.
```

---

## Context

The current AI News Monitor is close to a public GitHub release candidate. It already has:

- Local-first 24/7 monitoring
- Browser/local console
- Fast Alert default mode
- Source library
- Multiple notifiers
- Diagnostics
- Chinese/English i18n
- GPL-3.0-only license
- AI-assisted development disclosure
- GitHub Actions
- Release checklist

The next improvement should **not** add unrelated features. The goal is to improve the core reason this product exists:

> A reliable 24/7 information radar that pulls from enough high-quality Chinese and English public sources, understands which sources are trustworthy and fresh, detects when coverage is weak or stale, and sends the user timely high-quality alerts.

This iteration is inspired by public architectural ideas from mature monitoring systems, but the project must **not copy external project code, UI, data, feed lists, docs, or assets**.

---

# Non-negotiable rules

## 1. Do not copy external project code or data

Do not copy code, feed lists, UI, documentation wording, assets, schemas, or proprietary implementation details from external repositories.

It is acceptable to implement original code based on high-level ideas such as:

- Source tiering
- Source freshness states
- Intelligence gap reporting
- Last-known-good cache
- Smart polling/backoff
- Source package presets
- Health dashboards

## 2. Source code English-only

All source code must remain English-only.

This includes:

- Python source
- Tests
- Scripts
- GitHub Actions
- Comments
- Docstrings
- Embedded HTML/CSS/JS
- UI string keys in code

Chinese text is allowed only in:

- `locales/zh-CN.*`
- `README.zh-CN.md`
- Chinese documentation resources

Do not hard-code Chinese UI text in source code.

## 3. No real secrets or private runtime data

Do not add or assume real:

- API keys
- Webhooks
- Gmail app passwords
- SMTP credentials
- Telegram tokens
- WeCom keys
- WeChat/QQ relay keys
- Personal emails
- Real user prompts
- Real runtime data

Tests must use mocks, local fake services, monkeypatching, or placeholders.

## 4. Keep it lightweight

Avoid heavy dependencies and architectural rewrites. Prefer:

- Existing Python architecture
- Existing local server/browser console
- Existing PySide integration if present
- Existing source/notifier abstractions
- Small, testable modules
- Lightweight data structures
- SQLite/local storage if needed
- No mandatory cloud infrastructure

## 5. Preserve public GitHub readiness

Keep or improve:

- GPL-3.0-only license
- README language switching
- AI_DISCLOSURE.md
- SECURITY.md
- CONTRIBUTING.md
- SOURCE_GUIDE.md
- NOTIFICATION_GUIDE.md
- docs/RELEASE_CHECKLIST.md
- GitHub Actions
- No committed secrets
- No proprietary fonts/assets

---

# Main objective

Implement a **Source Reliability, Freshness & Intelligence Gaps Upgrade**.

The app should tell the user not only:

```text
Here are matching articles.
```

but also:

```text
Which source tier did they come from?
Are the important source groups fresh?
Which source groups are stale or failing?
Is this event confirmed by multiple independent sources?
Is the current topic coverage strong or weak?
Which sources are missing, empty, or degraded?
```

---

# Workstream A — Source Tiering and Reliability Metadata

## Goal

Make source quality explicit and easy to understand.

## Requirements

Add or extend source metadata with:

```yaml
source_tier: 1          # 1, 2, 3, or 4
source_role: "official" # official | wire | major_media | niche_media | company_ir | aggregator | blog | custom
state_affiliated: false
propaganda_risk: "low" # low | medium | high | unknown
editorial_context: ""
```

## Tier definitions

Use these definitions in docs and UI:

```text
Tier 1: Official, primary, wire, or direct company/organization sources.
Tier 2: Major mainstream media or well-established financial/technology media.
Tier 3: Specialist, niche, local, or domain-specific sources.
Tier 4: Aggregators, blogs, repost-heavy sources, or low-confidence custom sources.
```

## Source scoring integration

Update scoring so source tier and role influence ranking:

- Tier 1 should receive the strongest reliability boost.
- Official and company IR sources should receive role-specific boosts.
- Tier 4 and aggregator/blog sources should receive lower default trust.
- State affiliation and propaganda risk should not automatically block a source, but should be visible and may lower trust if configured.
- User whitelist/blacklist must still override normal scoring rules where configured.

## UI requirements

Source cards should show:

- Tier badge
- Role badge
- State-affiliated indicator if true
- Propaganda risk indicator
- Reliability score
- Explanation tooltip/help text

Example user-facing context:

```text
Tier 1 · Official source · High reliability
```

or:

```text
Tier 4 · Aggregator · Use with caution
```

## Config requirements

Update `config.example.yaml` and source library entries to include these fields where appropriate.

Do not require users to fill all fields for custom sources. Provide defaults:

```yaml
source_tier: 4
source_role: "custom"
propaganda_risk: "unknown"
state_affiliated: false
```

## Tests

Add tests for:

- Source tier parsing.
- Default metadata for custom sources.
- Tier-based scoring.
- Official/company IR boost.
- Tier 4 lower trust.
- UI/status serialization of tier metadata.

---

# Workstream B — Source Freshness States

## Goal

Make source health and freshness clear.

## Freshness states

Implement these source states:

```text
fresh
stale
very_stale
no_data
error
disabled
unknown
```

Suggested meanings:

```text
fresh: source succeeded recently within configured freshness window
stale: source has not succeeded recently but is not critically old
very_stale: source has not succeeded for a long time
no_data: source request succeeded but returned no usable articles
error: source request failed
disabled: source is disabled
unknown: no test/fetch history yet
```

## Configurable thresholds

Add config defaults:

```yaml
source_health:
  fresh_within_minutes: 30
  stale_after_minutes: 120
  very_stale_after_minutes: 360
  max_consecutive_failures_before_degraded: 3
```

## Source health fields

For each source, track:

- Last fetch time
- Last success time
- Last failure time
- Last error category
- Last error message
- Consecutive failures
- Last returned article count
- Average fetch latency if practical
- Freshness state

Persist this state locally where appropriate so the dashboard remains useful across restarts.

## UI requirements

In Source Library and Dashboard, show:

- Freshness badge
- Last success time
- Consecutive failures
- Last returned article count
- Failure reason
- Test source button

Use clear status colours:

- Fresh: calm green/blue
- Stale: amber
- Very stale/error: red/orange
- No data: grey
- Disabled: muted

Keep colours accessible and not overly harsh.

## Tests

Add tests for:

- Fresh state.
- Stale state.
- Very stale state.
- No-data state.
- Error state.
- Disabled state.
- Threshold configuration.
- Persistence/serialization where implemented.

---

# Workstream C — Intelligence Gaps Panel

## Goal

Show the user where coverage is weak, stale, or failing.

This prevents the user from misinterpreting silence as “no news”.

## Definition

An intelligence gap means:

```text
A source category, source package, or topic-critical source group is disabled, stale, empty, or failing in a way that reduces monitoring confidence.
```

## Required gap groups

Compute gaps by:

- Source package
- Source category
- Topic-relevant category
- Language
- Official/government sources
- Finance sources
- China/Taiwan sources
- Semiconductor/AI sources
- Company IR sources

## UI requirements

Add an **Intelligence Gaps** card/panel to the Dashboard and local browser console.

Show:

- Healthy groups
- Degraded groups
- Critical gaps
- Reason
- Recommended action

Examples:

```text
Official/Government sources: degraded — 2 enabled sources are stale.
China/Taiwan sources: critical — no enabled sources returned data in the last 6 hours.
Semiconductor/AI sources: healthy — 5 fresh sources.
```

## Notification behavior

Do not spam gap notifications by default. However, allow optional local dashboard warnings.

Optional config:

```yaml
intelligence_gaps:
  enabled: true
  notify_on_critical_gap: false
  critical_gap_cooldown_minutes: 360
```

## Tests

Add tests for:

- Healthy group.
- Degraded group.
- Critical gap.
- Disabled category.
- Language-specific gap.
- Topic-relevant gap.
- Gap summary serialization.

---

# Workstream D — Source Cache and Last-Known-Good Fallback

## Goal

Make fetch cycles resilient when some sources fail.

## Requirements

Implement source-level caching:

```yaml
source_cache:
  enabled: true
  source_ttl_seconds: 600
  digest_ttl_seconds: 900
  last_known_good_enabled: true
  last_known_good_max_age_hours: 24
```

## Behavior

For each source:

1. If cache is fresh, reuse cached entries where appropriate.
2. If fetch succeeds, update cache and last-known-good.
3. If fetch fails but last-known-good is available and not too old, return cached entries with a degraded marker.
4. Do not treat last-known-good entries as fresh.
5. Clearly mark cached/degraded items in diagnostics and dashboard.
6. Avoid duplicate alerts from cached data.

## Alert behavior

Cached last-known-good articles should generally not generate new alerts unless:

- They were never alerted before.
- The user explicitly enables cached fallback alerting.
- They are within acceptable age thresholds.

Default should avoid stale alert spam.

Suggested config:

```yaml
source_cache:
  allow_cached_alerts: false
```

## Tests

Add tests for:

- Cache hit.
- Cache miss.
- Fetch success updates cache.
- Fetch failure uses last-known-good.
- Expired last-known-good is not used.
- Cached articles do not generate duplicate alerts.
- Diagnostics show degraded cached state.

---

# Workstream E — Smart Polling and Backoff

## Goal

Make 24/7 monitoring more stable by adapting to failures.

## Requirements

Implement source-level polling backoff:

```yaml
smart_polling:
  enabled: true
  failure_backoff_multiplier: 2.0
  max_backoff_minutes: 60
  reset_after_success: true
```

Behavior:

- If a source fails repeatedly, increase its next fetch delay.
- If a source succeeds, reset its backoff.
- Do not let one failing source block the entire monitoring cycle.
- Keep per-source timeout.
- Keep an overall cycle deadline if practical.
- Record current backoff state in source health.

## Suggested fetch limits

Add or preserve sensible defaults:

```yaml
fetching:
  per_source_timeout_seconds: 8
  overall_cycle_deadline_seconds: 40
  max_articles_per_source: 10
  max_candidate_articles_per_topic: 5
```

## UI requirements

Source cards should show if a source is in backoff:

```text
Backoff active · next retry in 12 minutes
```

## Tests

Add tests for:

- Backoff increases after failures.
- Backoff resets after success.
- Source in backoff is skipped until next retry.
- Failing source does not block healthy source.
- Overall cycle still completes.

---

# Workstream F — Multi-Source Confirmation Boost

## Goal

Increase trust when multiple independent sources report the same event.

## Requirements

Improve or add event clustering for scoring.

Use lightweight methods only:

- Normalized title similarity
- Shared entities/keywords
- Same date/time window
- Same topic
- Source independence
- Optional LLM confirmation only if already available and cost-controlled

Do not create heavy embedding/vector dependencies unless already present and justified.

## Scoring

Add or improve:

```yaml
quality:
  multi_source_confirmation_boost: 0.15
  independent_source_bonus: 0.05
  same_owner_confirmation_penalty: 0.05
```

Behavior:

- If multiple independent sources report the same event, boost confidence.
- If sources are from the same owner/network, reduce confirmation strength.
- If one source is official and another is reputable media, boost more.
- Show explanation in alert:

```text
Confirmed by 3 sources: Official source + 2 major media sources.
```

## Tests

Add tests for:

- Same-event cluster detection.
- Independent sources boost.
- Same-owner penalty.
- Official + media confirmation.
- Alert explanation includes confirmation context.

---

# Workstream G — Source Package Presets

## Goal

Make source configuration easier and more relevant to monitoring goals.

## Existing packages

Preserve existing source packages if present.

Add/improve these presets:

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

## Preset behavior

Each preset should define:

- Recommended sources
- Recommended categories
- Suggested source tier weights
- Suggested refresh interval
- Suggested relevance threshold
- Optional topic starter examples

Do not force-enable everything. Let users preview and apply.

## UI requirements

Add source preset cards:

- Preset name
- Description
- Number of sources
- Expected coverage
- Recommended use case
- Apply/preview button

## Tests

Add tests for:

- Preset parsing.
- Applying a preset.
- Preset does not overwrite unrelated custom settings.
- Preset source count and categories.

---

# Workstream H — Coverage Quality Score

## Goal

Give the user a high-level confidence indicator for whether the current monitor coverage is reliable.

## Requirements

Add a coverage quality score per topic and/or globally.

Inputs:

- Fresh source count
- Enabled source count
- Tier 1/2 source availability
- Category coverage
- Language coverage
- Consecutive failures
- Intelligence gaps
- Recent article volume

Output:

```text
coverage_quality: high | medium | low | critical
```

Examples:

```text
High: 8 fresh sources, 3 Tier 1 sources, no critical gaps.
Medium: Some stale sources but adequate coverage.
Low: Few fresh sources or missing a critical category.
Critical: No fresh sources for key categories.
```

## UI requirements

Dashboard should show:

- Global coverage quality
- Per-topic coverage quality if feasible
- Main reason for score
- Recommended action

## Tests

Add tests for:

- High coverage.
- Medium coverage.
- Low coverage.
- Critical coverage.
- Reason generation.

---

# Workstream I — Dashboard and Local Console Updates

## Goal

Surface reliability and freshness clearly in the operator UI.

## Dashboard additions

Add or improve:

- Source freshness summary
- Intelligence gaps panel
- Coverage quality score
- Source backoff summary
- Last-known-good/cached usage summary
- Multi-source confirmation summary for recent alerts
- Source tier distribution
- Top failing sources

## Local console endpoints

Add or improve JSON endpoints if practical:

```text
/source-health
/intelligence-gaps
/coverage-quality
/source-packages
```

Keep endpoints local-only by default.

## UI style

Keep the design:

- Lightweight
- Apple-like
- Low-glare
- Modular
- Readable
- English/Chinese i18n through locale resources only

## Tests

Add endpoint tests where feasible.

---

# Workstream J — Documentation Updates

Update:

- `README.md`
- `README.zh-CN.md`
- `SOURCE_GUIDE.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/RELEASE_CHECKLIST.md`
- `config.example.yaml`

## Document

- Source tiers
- Source roles
- Propaganda/state-affiliation indicators
- Fresh/stale/very stale/no data/error states
- Intelligence gaps
- Last-known-good cache
- Smart polling/backoff
- Source presets
- Coverage quality
- Multi-source confirmation
- Limitations and non-goals

## Important disclaimer

Keep documentation clear that:

- The app monitors public information sources.
- It does not bypass paywalls.
- It does not simulate login.
- It does not scrape private sources.
- It does not provide financial advice.
- It does not execute trades.

---

# Workstream K — Tests and Release Readiness

## Required tests

Add or update tests for:

1. Source tier metadata parsing.
2. Source role metadata parsing.
3. Source freshness state computation.
4. Intelligence gap detection.
5. Source cache hit/miss.
6. Last-known-good fallback.
7. Cached article no-alert default behavior.
8. Smart polling backoff increase/reset.
9. Failing source does not block healthy source.
10. Multi-source confirmation boost.
11. Same-owner confirmation penalty.
12. Source preset parsing/apply behavior.
13. Coverage quality score.
14. Dashboard/local endpoint serialization.
15. i18n keys for new UI strings.
16. No Chinese in source code.
17. Config example parses.
18. Existing notification/LLM/source diagnostics still pass.
19. GitHub Actions still pass.

## Manual release checklist

Update `docs/RELEASE_CHECKLIST.md` with manual checks for:

- Source freshness panel.
- Intelligence gaps panel.
- Source package presets.
- Source backoff.
- Cached/last-known-good behavior.
- Coverage quality score.
- Multi-source confirmation explanation.

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

## Source reliability changes
- ...

## Freshness and gap tracking
- ...

## Cache and backoff
- ...

## Multi-source confirmation
- ...

## Source presets
- ...

## UI/dashboard changes
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

- Source tiering exists and affects scoring.
- Source freshness states exist and are visible.
- Intelligence gaps are computed and shown.
- Source cache and last-known-good fallback are implemented or clearly scaffolded.
- Smart polling/backoff works.
- Multi-source confirmation boosts high-quality alerts.
- Source presets are easier to apply.
- Coverage quality score exists.
- Dashboard/local console surfaces all reliability states.
- Documentation explains the new concepts.
- Tests cover the new behavior.
- Source code remains English-only.
- No secrets are committed.
- The project remains lightweight and public-GitHub-ready.

---

## 08. GitHub upload readiness prompt

Source file before consolidation: `08-ai_news_monitor_github_upload_readiness_prompt.md`

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

---

## 09. E2E operational closure prompt

Source file before consolidation: `09-ai_news_monitor_e2e_operational_closure_prompt.md`

# AI News Monitor — E2E Operational Closure & Concise Browser Console Prompt

## Recommended Codex CLI command

Place this file in the repository root, then run Codex CLI from the repository root:

```text
/goal Read ./ai_news_monitor_e2e_operational_closure_prompt.md carefully and implement everything described in it. Treat this file as the authoritative next-iteration specification. Before coding, read CHATBOT_CONTEXT.md, HANDOFF.md, NEXT_VERSION_MONITORING_REPORT.md, CURRENT_RUNTIME_STATUS.json, README.md, README.zh-CN.md, SOURCE_GUIDE.md, NOTIFICATION_GUIDE.md, docs/RELEASE_CHECKLIST.md, config.example.yaml, src/, tests/, locales/, and .github/workflows/. Do not assume real API keys, real Gmail credentials, real webhook tokens, or real runtime data. Focus on proving the full fetch→candidate→LLM→alert→notification chain, fixing source/runtime blockers, and making the browser console concise, readable, and useful. Keep source code English-only, keep Chinese only in locale/documentation resources, do not expose secrets, run tests after each milestone, and finish with a requirement-by-requirement audit.
```

---

## Current situation

The latest version has implemented source reliability, freshness states, intelligence gaps, source cache, smart polling/backoff, source packages, and coverage quality. However, current observed runtime status shows the system has not yet proven the full E2E alert delivery chain:

```text
Fetched articles: yes
Candidates: 0
Alerts sent: 0
Notifications sent: 0
Coverage quality: critical
```

A screenshot of the browser console shows another important issue:

- The browser console displays too much raw technical detail directly in cards.
- Long URLs, raw HTTP errors, raw JSON event fragments, and code-like log text overflow the layout.
- Important information is buried inside noisy raw output.
- The browser side should be a concise operator console, not a raw debug dump.

This iteration must close the operational loop and improve the browser console information design.

---

# Non-negotiable rules

## 1. No real secrets or private data

Do not add, assume, commit, print, or log real:

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
- Real runtime credentials

Use mocks, dummy values, fake SMTP, monkeypatching, or local fixtures in tests.

## 2. Source code English-only

All source code must remain English-only.

Chinese text is allowed only in:

- `locales/zh-CN.*`
- `README.zh-CN.md`
- Chinese documentation resources

Do not hard-code Chinese UI strings in Python, HTML templates, JavaScript, tests, or scripts. Use i18n resource keys.

## 3. Keep the app lightweight

Do not introduce heavy frontend frameworks. Use the existing local server/browser console architecture and lightweight HTML/CSS/JS where possible.

## 4. Do not copy external project code/data

Only use architecture ideas. Do not copy code, data, feed lists, UI, assets, or documentation from external repositories.

---

# Main goals

This iteration has two main goals:

## Goal A — E2E operational closure

Prove and improve the actual chain:

```text
source fetch
→ language filter
→ keyword/prompt match
→ deduplication
→ candidate ranking
→ LLM analysis/summary
→ alert creation
→ notification delivery
→ visible app/browser feedback
```

The user must be able to run a controlled E2E test and see exactly where the pipeline succeeds or fails.

## Goal B — Concise and usable browser console

The browser console must become a compact operator dashboard:

- No raw code-like log overflow in main cards.
- No long unwrapped URLs breaking layouts.
- No raw JSON flood in user-facing panels.
- Show concise summaries first.
- Keep detailed technical information behind expandable panels.
- Provide clear actions and recommended fixes.
- Make the UI useful at a glance.

---

# Workstream A — E2E Test Mode / Run Once

## Objective

Add a safe, deterministic E2E test path so the user can confirm that the system can:

1. Fetch at least one test article.
2. Produce at least one candidate.
3. Run LLM summary/analysis.
4. Save one alert.
5. Send one notification to enabled channels.
6. Display the result in the app/browser console.

## Requirements

Add one or both of these options:

### Option 1: Run Once

Add a **Run Once** or **Run One Cycle** action that executes one monitor cycle immediately and reports the result.

### Option 2: E2E Test Mode

Add a dedicated **E2E Test Mode** that uses a controlled mock/local source if needed. This mode should not depend on live news availability.

The test mode may use a built-in local fixture article such as:

```text
Title: OpenAI announces new AI infrastructure partnership with NVIDIA
Language: en
Source: E2E Test Source
URL: https://example.test/e2e-openai-nvidia
Snippet: A controlled test article used to verify the monitoring pipeline.
```

Rules:

- The test fixture must be clearly marked as test-only.
- Test mode should never be confused with real news.
- It should produce a visible test alert.
- It should send a test notification if notifications are enabled.
- It should respect secret redaction.
- It should be safe for public release.

## E2E result report

After Run Once or E2E Test Mode, show a concise report:

```text
E2E result: success / partial / failed

Fetched: 10
Language accepted: 10
Keyword matched: 3
After deduplication: 2
Candidates ranked: 2
LLM analyzed: 1
Passed threshold: 1
Alerts saved: 1
Notifications sent: 1
```

If failed, show exactly where it failed.

## Tests

Add tests for:

- E2E fixture source produces candidate.
- E2E fixture can generate alert.
- E2E fixture notification path uses mock notifier.
- Run Once emits pipeline summary.
- Test mode is clearly marked and does not pollute production data unexpectedly.

---

# Workstream B — Pipeline Funnel Diagnostics

## Objective

When the app fetches many articles but sends zero alerts, users must know why.

## Requirements

Implement a pipeline funnel summary for each monitor cycle:

```text
Cycle started at
Sources attempted
Sources succeeded
Sources failed
Articles fetched
Articles accepted by language
Articles rejected by language
Articles rejected by keyword/prompt filter
Articles rejected as duplicates
Candidates ranked
Candidates sent to LLM
LLM accepted
LLM rejected
Rejected below threshold
Alerts saved
Notifications attempted
Notifications succeeded
Notifications failed
Cycle duration
```

## Rejection reasons

Track top rejection reasons:

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
```

## UI requirements

Show the latest pipeline funnel in Dashboard and Diagnostics.

Keep it concise:

```text
Fetched 441 → Language 390 → Keyword 12 → New 3 → LLM 2 → Alerts 0
```

Then provide expandable details:

```text
Why no alerts?
- 378 no keyword match
- 9 duplicates
- 2 score below threshold
```

## Tests

Add tests for:

- Funnel counts are recorded.
- Rejection reasons are aggregated.
- Zero-alert cycle explains why.
- Dashboard serialization includes concise funnel.
- Raw debug data is not shown in the main summary.

---

# Workstream C — Browser Console Information Design and Overflow Fix

## Current problem

The browser console currently displays raw technical text directly in cards:

- Long GDELT query URLs overflow.
- Yahoo 429 raw error text overflows.
- Raw JSON event fragments appear in the main event panel.
- Cards become hard to read.
- Important status is buried in noise.

## Objective

Make the browser console highly concise, readable, and operationally useful.

## Requirements

### 1. Do not show raw technical blobs by default

Main cards should show summaries such as:

```text
GDELT: error · JSON parse failure · 3 failures
Yahoo Finance RSS: rate limited · retry later
Google News RSS: fresh · 10 articles
```

Do not show full URLs, raw stack traces, raw JSON, or full exception strings in primary cards.

### 2. Use expandable details

For every diagnostic item, provide:

```text
Summary line
Status badge
Suggested action
Details disclosure
```

Technical details should be hidden behind:

```text
Show details
Copy diagnostics
```

### 3. Wrap and truncate safely

Update CSS/layout so long content never breaks cards:

```css
overflow-wrap: anywhere;
word-break: break-word;
max-width: 100%;
```

For long URLs, use:

- Middle truncation if practical.
- Copy button for full URL.
- Tooltip or expandable detail.

### 4. Limit raw event display

The "Real-time Events" panel should not show endless raw JSON.

Show event rows like:

```text
16:20 source_fetch · GDELT · failed
16:21 cycle_completed · 0 alerts
16:22 status · Running
```

Details can be expanded.

Limit the visible list to the latest N events, for example 50.

### 5. Status cards should be compact

Dashboard cards should show:

- Key metric
- Short label
- Optional status badge
- No raw logs

### 6. Console sections

Ensure browser console includes concise sections:

- Overview
- Pipeline Funnel
- Source Health
- Intelligence Gaps
- Coverage Quality
- Notification Health
- Recent Alerts
- Recent Events
- Diagnostics

### 7. Visual fixes

- Fix card overflow.
- Fix scroll areas.
- Improve spacing.
- Keep the browser console lightweight.
- Maintain Apple-like font stack.
- Keep source code English-only and move Chinese text to locale resources.

## Tests

Add tests/static checks for:

- Browser HTML/CSS contains overflow-safe rules.
- Event serialization has concise fields.
- Raw event JSON is not the primary display.
- Long URLs are summarized/truncated in user-facing fields.
- Details still contain diagnostic data when requested.

---

# Workstream D — GDELT Production Diagnostic Parity

## Current issue

Runtime report indicates:

```text
GDELT production monitor query failed with JSON parse error.
A smaller diagnostic query may pass.
```

This means diagnostic and production query paths may not be equivalent.

## Requirements

1. Make GDELT diagnostics use the same query construction logic as production, or explicitly test both:
   - Simple diagnostic query.
   - Production-shaped topic query.

2. Handle non-JSON responses safely:
   - Do not call `response.json()` without checking content type / body.
   - Capture status code.
   - Capture a short redacted response preview.
   - Classify the error.

3. Classify likely failures:
   - `api_rate_limited`
   - `api_bad_response`
   - `api_timeout`
   - `base_url_unreachable`
   - `feed_parse_failed`
   - `unknown_error`

4. If GDELT query is too long or malformed, detect and report:
   - query too long
   - unsupported query shape
   - invalid encoded query

5. Provide suggested fix:
   - Reduce keywords.
   - Use fewer OR terms.
   - Try Google News RSS fallback.
   - Wait for rate limit/backoff.

## Tests

Add tests for:

- GDELT non-JSON response.
- GDELT 429.
- GDELT long query classification.
- Production-shaped diagnostic query.
- Safe response preview redaction.

---

# Workstream E — Yahoo Finance 429 Handling

## Current issue

Runtime report shows Yahoo Finance RSS returning:

```text
429 Too Many Requests
```

## Requirements

1. Classify Yahoo 429 as `api_rate_limited`, not generic error.
2. Put Yahoo sources into backoff after 429.
3. Show concise UI status:

```text
Yahoo Finance RSS: rate limited · next retry in 30 minutes
```

4. Do not spam logs or dashboard with repeated raw 429 messages.
5. Add alternative finance sources in source packages if already available and public.
6. Ensure Finance Starter does not depend on a single rate-limited source.

## Tests

Add tests for:

- Yahoo 429 classification.
- Backoff after 429.
- UI serialization of rate-limited status.
- Finance package remains usable with alternative source if configured.

---

# Workstream F — Email Health Consistency

## Current issue

Runtime report indicated a mismatch:

```text
Email health may show ok while setup diagnostics still indicates From Address problems.
```

## Requirements

1. Email health check must validate all required fields:
   - SMTP host
   - SMTP port
   - encryption
   - username
   - password/app password
   - from address
   - recipients

2. If `from_address` is missing or invalid, health must not be `ok`.

3. If `from_address` differs from username, warn clearly. Do not necessarily fail if SMTP provider allows it, but show warning.

4. UI should show:
   - required fields complete / incomplete
   - warning if from != username
   - test email result

5. Align:
   - setup required fields
   - notifier health
   - test email diagnostics
   - config validation

## Tests

Add tests for:

- Missing from address makes Email not ready.
- Invalid from address classified.
- From != username warning.
- Health and setup diagnostics agree.
- Existing Gmail preset still works.

---

# Workstream G — Health vs Readiness

## Current issue

`/health` returns ok when the server is alive, but this may be misread as full monitoring health.

## Requirements

Keep `/health` as server liveness.

Add or improve `/readiness` or `/api/readiness`.

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

## UI requirement

Clearly distinguish:

```text
Server: alive
Monitor: running/paused/stopped
Coverage: high/medium/low/critical
Notifications: ready/degraded/not ready
LLM: ready/error/not configured
```

Do not let users believe "server alive" means "monitor fully healthy".

## Tests

Add tests for:

- `/health` liveness.
- `/readiness` healthy state.
- `/readiness` degraded state.
- Critical coverage affects readiness.
- Missing notifier affects readiness.

---

# Workstream H — Paused/Running State Visibility

## Current issue

The app may be paused while the user thinks it is running.

## Requirements

Make monitor state highly visible:

- Running
- Paused
- Stopped
- Backoff
- Error

Show:

- Current state badge
- Last cycle time
- Next scheduled cycle time
- Pause reason if available
- Resume button if paused
- Start button if stopped

If paused, the Dashboard should show a prominent but calm warning:

```text
Monitoring is paused. No new alerts will be sent until you resume.
```

## Tests

Add tests for:

- Paused state serialized.
- Dashboard contains paused warning.
- Resume action updates state.
- Start/stop/resume actions publish events.

---

# Workstream I — Source Package Enablement Visibility

## Current issue

Runtime status showed `source_packages_enabled` may be empty while the user expects coverage.

## Requirements

Show source package state clearly:

- Enabled packages
- Disabled recommended packages
- Sources included in each package
- Effective enabled source count
- Effective fresh source count

If no source packages are enabled, show:

```text
No source packages enabled. Enable at least one source package or custom source.
```

If enabled packages have no fresh sources, show:

```text
Enabled packages are not fresh. Test sources or add alternative sources.
```

## Tests

Add tests for:

- No packages enabled warning.
- Enabled package with no fresh sources warning.
- Package source counts.
- Package freshness serialization.

---

# Workstream J — Alert Threshold Test Guidance

## Current issue

Real runtime rejected candidates because scores were below the topic threshold.

This is correct behavior, but users need guidance.

## Requirements

When zero alerts are produced because of threshold:

1. Show rejected below threshold count.
2. Show top rejected candidate score.
3. Show topic threshold.
4. Suggest test-mode changes:

```text
For E2E testing, lower threshold to 50-60 or use Test Mode.
For production, keep threshold high to reduce noise.
```

5. Add optional "temporary E2E threshold" for test mode only.

## Tests

Add tests for:

- Below-threshold rejection explanation.
- Top rejected candidate summary.
- Test-mode threshold override does not change production config.

---

# Workstream K — Documentation Updates

Update:

- README.md
- README.zh-CN.md
- SOURCE_GUIDE.md
- NOTIFICATION_GUIDE.md
- docs/RELEASE_CHECKLIST.md
- docs/ARCHITECTURE.md if needed
- config.example.yaml

## Must document

- E2E Test Mode / Run Once
- Pipeline Funnel
- What "0 alerts" means
- How to interpret coverage critical
- Difference between `/health` and readiness
- GDELT/Yahoo common errors
- Source package enablement
- Threshold tuning for testing vs production
- Browser console concise vs details behavior

---

# Workstream L — Tests

Add or update tests for:

1. E2E test fixture produces alert.
2. Run Once produces funnel summary.
3. Pipeline funnel counts.
4. Zero-alert rejection explanation.
5. Browser console does not display raw JSON as primary event text.
6. Browser console overflow-safe CSS exists.
7. Long URL diagnostics are summarized/truncated.
8. GDELT non-JSON response classification.
9. GDELT 429 classification.
10. GDELT long query classification.
11. Yahoo 429 classification.
12. Yahoo backoff.
13. Email health checks from address.
14. Setup diagnostics and notifier health agree.
15. `/readiness` endpoint healthy/degraded states.
16. Paused state visibility.
17. Source package warnings.
18. Threshold guidance.
19. Existing source reliability/freshness tests still pass.
20. Existing notification/LLM diagnostics tests still pass.
21. No Chinese in source code.
22. Config example parses.
23. GitHub Actions unaffected.

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

## E2E operational closure
- ...

## Pipeline funnel
- ...

## Browser console cleanup
- ...

## Source/runtime fixes
- GDELT:
- Yahoo:
- Source packages:
- Coverage:
- Readiness:

## Email health consistency
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

- A user can run a controlled E2E test that produces a visible test alert and notification through mocked or configured channels.
- The dashboard shows a clear pipeline funnel explaining where articles are filtered out.
- Browser console main cards are concise and do not show raw code-like overflow.
- Long URLs and raw JSON do not break the layout.
- Technical details are available only via expandable details/copy diagnostics.
- GDELT production-shaped diagnostics are safe and classify failures.
- Yahoo 429 is classified and backoff is visible.
- Email readiness validates From Address consistently.
- `/health` and readiness are clearly separated.
- Paused/running state is obvious.
- Source package enablement and freshness are obvious.
- Zero-alert cycles are explainable.
- Tests cover the new behavior.
- Source code remains English-only.
- No secrets are committed.
- The project remains lightweight and ready for GitHub release.

---

## 10. Final GitHub upload cleanup prompt

Source file before consolidation: `10-ai_news_monitor_final_github_upload_cleanup_prompt.md`

# AI News Monitor — Final GitHub Upload Cleanup Prompt

## Recommended Codex CLI command

Place this file in the repository root, then run Codex CLI from the repository root:

```text
/goal Read ./ai_news_monitor_final_github_upload_cleanup_prompt.md carefully and implement everything described in it. Treat this file as the authoritative final GitHub-upload cleanup specification. Before coding, read CHATBOT_CONTEXT.md, HANDOFF.md, NEXT_VERSION_MONITORING_REPORT.md, README.md, README.zh-CN.md, SOURCE_GUIDE.md, NOTIFICATION_GUIDE.md, docs/RELEASE_CHECKLIST.md, config.example.yaml, src/, tests/, locales/, .github/workflows/, .gitignore, pyproject.toml, requirements.txt, and requirements-dev.txt. Do not assume real API keys, real Gmail credentials, real webhook tokens, real notification targets, or real runtime data. Do not push to GitHub or create a remote. Focus only on making the local repository clean, safe, professional, and ready for a first private GitHub push. Keep source code English-only, keep Chinese only in locale/documentation resources, avoid broad feature changes, run tests/checks after each milestone, and finish with a GitHub-upload readiness audit plus exact next commands for the user.
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
ai_news_monitor_source_reliability_freshness_prompt.md
ai_news_monitor_github_upload_readiness_prompt.md
ai_news_monitor_next_iteration_prompt.md
phase_verification_prompt.md
ai_news_monitor_pre_github_interface_stabilization_prompt.md
codex_next_phase_prompt.md
ai_news_monitor_final_target_candidate_prompt.md
ai_news_monitor_e2e_operational_closure_prompt.md
codex_prompt_ai_news_monitor.md
codex_update_prompt.md
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

## 11. Phase verification prompt

Source file before consolidation: `11-phase_verification_prompt.md`

# Phase Verification Prompt

## Objective

Verify that the AI News Monitor application has implemented all mandatory features from the next phase specification and runs successfully on your machine. Perform the following tasks in sequence and record your observations.

1. **Environment Setup**
   - Ensure your working directory contains the latest source code for the AI News Monitor and the updated specification file.
   - Confirm that `.env` and `config.yaml` files exist and include valid API keys for the LLM and translation services, as well as dummy notification endpoints for Email and each chat channel (WeCom, Telegram, WeChat/QQ via ServerChan if supported).  If any secrets are missing, note the issue and stop.

2. **Build and Run**
   - Use the provided packaging script or instructions to build the application for your platform (Windows or macOS).  Capture any build warnings or errors.
   - Launch the built application.  Confirm that it starts correctly and opens the local UI at `http://localhost:<port>`.

3. **Functional Checks**
   - **Multilingual Input:** Create a monitoring rule with keywords in both Chinese and English.  Verify that news items from Chinese and English sources are fetched and displayed.  Translation should occur automatically when the language of the article differs from the selected UI language.
   - **Language Toggle:** Use the language toggle in the settings to switch between Chinese and English.  Ensure that all interface text, notifications, and logs update instantly and consistently to the selected language.
   - **Notifications:** Configure each available notifier (Email, WeCom, Telegram, WeChat/QQ).  Use dummy addresses or webhooks where necessary.  Send a test notification through each channel and verify that the status indicator reports success and records the time of the last message.
   - **UI Design:** Observe the UI aesthetics.  Confirm that it follows the minimalist Apple‑inspired design with generous white space, clean fonts, a restrained colour palette and subtle animations.  Interactions such as opening dialogs or expanding configuration panels should be smooth and non‑blocking.
   - **Real‑Time Updates:** Ensure that new articles appear in the UI without needing to refresh the page, using SSE or WebSockets.  Watch the live indicator or notification banner for updates.

4. **Stability Checks**
   - Let the application run for at least five minutes.  Observe whether memory usage grows abnormally or whether any errors appear in the log.  Check that all notifier channels remain connected and attempt automatic reconnection if a connection drops.
   - Test the retry logic by intentionally disconnecting one notification service (e.g. disable internet on the computer) and then re‑enable it.  Confirm that notifications resume automatically.

5. **Summary**
   - Provide a detailed summary indicating which features are fully functional, partially implemented, or missing.  Include observations about build quality, UI consistency, translation accuracy, notifier stability and real‑time updates.
   - Highlight any bugs, performance issues or design discrepancies you discovered.
   - Suggest concrete next steps to fix defects or finish incomplete features.

## Completion

When all checks are complete, output your findings in a structured report using the above “Summary” format.  Mark the task done once you have verified the phase completion.
