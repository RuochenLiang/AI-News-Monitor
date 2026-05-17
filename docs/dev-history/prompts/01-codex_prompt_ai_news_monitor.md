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
