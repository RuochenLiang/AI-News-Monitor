# Codex Prompt: AI-News-Monitor Runtime + Web UI Stabilization Pass

You are working on the `AI-News-Monitor` repository.

## Required reading before coding

Read these files first if they exist:

- `CHATBOT_CONTEXT.md`
- `HANDOFF.md`
- `docs/chatbot-progress-2026-05-24.md`
- `NEXT_VERSION_MONITORING_REPORT.md`
- `README.md`
- `README.zh-CN.md`
- `SOURCE_GUIDE.md`
- `NOTIFICATION_GUIDE.md`
- `config.example.yaml`
- `src/sources/gdelt.py`
- `src/sources/library.py`
- `src/source_reliability.py`
- `src/pipeline.py`
- `src/monitor.py`
- `src/llm_client.py`
- all web/frontend files
- all tests

Do not start by rewriting the project. This is a stabilization and release-readiness pass.

---

## Current confirmed situation

The project is close to a GitHub release candidate, but not fully ready.

Known good parts:

- LLM configuration appears to be working.
- Email notification appears to be working.
- Real alert delivery has already been proven.
- Structured Outputs support already appears implemented in `src/llm_client.py`.
- Tests for LLM schema/config have passed before.

Do **not** redo Structured Outputs unless you find a small bug.

Known unhealthy parts:

- Runtime readiness is degraded.
- Source coverage is too weak.
- Candidate generation is unstable.
- Some monitor cycles fetch articles but produce 0 ranked candidates.
- GDELT can fail with: `api_bad_response: The specified phrase is too short.`
- Yahoo Finance RSS can return `429 Too Many Requests`.
- Browser/web UI has serious display issues:
  - large blocks of raw code or JSON overflow outside containers
  - long strings break layout
  - console/status/detail panels are too verbose
  - Chinese and English are mixed in the UI
  - localization is incomplete or inconsistent
  - browser-side information is not concise enough for normal users

Main objective:

Make the project ready for a private GitHub push by improving runtime stability, source coverage, and web UI usability without changing the core product direction.

---

## Product principles

Preserve these principles strictly:

1. Keep core behavior stable or better.
2. Do not hardcode secrets, API keys, accounts, prompts, or passwords.
3. Keep features scriptable, configurable, and modular.
4. Global language choice must be consistent across the UI and outputs.
5. The frontend should be minimal, modern, clear, and Apple-style where reasonable.
6. Browser UI should show concise, useful information first.
7. Raw JSON/code/logs should never visually dominate normal user screens.
8. Long text must wrap safely and never overflow cards, panels, tables, modals, or log boxes.
9. Avoid large rewrites unless necessary.
10. Keep the repo clean and release-friendly.

---

# Task 1: Clean release root

The repository root should not contain scratch prompt files.

In particular, if this file exists in the root:

- `structured_outputs_upgrade_prompt.md`

Move it to:

- `docs/dev-history/prompts/12-structured-outputs-upgrade.md`

If a prompt archive index exists, update it.

Do not delete useful historical prompts unless they are duplicated elsewhere.

Add or update a test that fails if obvious scratch prompt files remain in the repository root.

---

# Task 2: Harden GDELT keyword/query generation

Improve `src/sources/gdelt.py` so topic keywords are sanitized before building GDELT queries.

Requirements:

- Strip trailing commas, semicolons, quotes, and punctuation fragments.
- Reject empty strings.
- Reject punctuation-only keywords.
- Reject meaningless fragments.
- Normalize whitespace.
- Avoid sending phrases that GDELT considers too short.
- Preserve useful technical keywords such as `AI`, `HBM`, `DRAM`, `DDR5`, `GPU`, `CPU`, and `TSMC` only when safely included in a valid query.
- Keep query length under the existing maximum limit.
- Do not make GDELT queries so broad that they become useless.

Add tests for malformed keywords such as:

- `HBM,`
- `DRAM,`
- `DDR5,`
- `"`
- `,`
- `AI,`
- empty strings
- whitespace-only strings

Expected result:

Generated GDELT queries should not trigger obvious `phrase too short` API errors.

---

# Task 3: Improve source package coverage defaults

Update source library/default source packages so these areas are covered or easy to enable:

- `global-news-starter`
- `finance-starter`
- `official-gov-starter`
- `semiconductor-ai-starter`
- `company-ir-starter`
- `china-taiwan-starter`
- `geopolitics-starter`
- `ai-industry-starter`
- `taiwan-semiconductor-official`

Prefer:

- RSS/Atom feeds
- official sources
- public institutional sources
- company IR/newsroom sources
- stable low-rate sources

Avoid:

- paywalled scraping
- login-only sources
- fragile HTML scraping where RSS exists
- making the app depend on rate-limited public APIs by default

Each source entry should include, where the schema supports it:

- `id`
- `name`
- `url`
- `category`
- `language`
- `reliability_score`
- `ownership`
- `bias_hint`
- `website_url`
- `packages`

Add or update tests that verify these packages are present and have meaningful enabled source coverage.

---

# Task 4: Add or enable Taiwan / Chinese-language / geopolitics / AI-industry sources

Add or enable reliable public sources for:

- Taiwan official policy/news
- Taiwan semiconductor ecosystem
- China/Taiwan geopolitics
- semiconductor trade policy
- AI infrastructure industry
- AI chips / GPU / CPU / HBM / networking / data center / power infrastructure
- Chinese-language or zh-CN-relevant sources

Do not overfit to one source type. Prefer a balanced source library.

Important:

- A `zh-CN` UI language setting does not mean every source must be mainland Chinese.
- Source language metadata should reflect the source content language accurately.
- The UI/output language should be controlled separately from source language.

---

# Task 5: Reduce public API pressure and classify failures clearly

Adjust default runtime settings to reduce rate-limit failures.

Requirements:

- Default polling interval should be safer for public sources, around 600 to 900 seconds.
- Manual `Run Once` should remain available for testing.
- Yahoo Finance RSS `429` should be non-fatal.
- Yahoo `429` should be classified as `api_rate_limited` or equivalent.
- The app should not appear broken just because one public source is rate-limited.
- If Yahoo Finance is too fragile as a default dependency, disable it by default or reduce its priority while keeping Finance Starter useful through alternatives.

Add tests for Yahoo/rate-limit classification if the codebase has such tests already.

---

# Task 6: Candidate funnel diagnostics

Improve diagnostics for monitor cycles where articles are fetched but 0 candidates are ranked.

The system should expose concise counts for:

- fetched articles
- rejected by language
- rejected by keyword/topic
- rejected by dedupe
- rejected by source coverage
- rejected by freshness
- rejected by threshold
- sent to LLM
- rejected by LLM
- notification sent

Requirements:

- Diagnostics must be human-readable.
- Do not spam raw JSON into the browser UI.
- Keep detailed raw data behind an expander/collapsible debug section.
- Make the normal UI useful to a non-developer.
- Keep logs useful for developers.

Add or update tests where practical.

---

# Task 7: Fix web UI code overflow

The web UI currently has large code/JSON/log overflow problems.

Fix frontend layout so no visible content overflows horizontally.

Apply safe wrapping/truncation to:

- raw code blocks
- JSON blocks
- logs
- URLs
- source IDs
- error messages
- stack traces
- long article titles
- long source names
- long prompt/config fields
- tables
- cards
- modal dialogs
- side panels
- status/diagnostic panels

Implementation expectations:

- Use `overflow-wrap: anywhere` or equivalent where appropriate.
- Use `word-break`, `white-space`, `max-width`, `overflow-x: auto`, and `text-overflow` thoughtfully.
- Code/log blocks may scroll horizontally inside their own container, but must not break the page layout.
- Tables must not force the page wider than the viewport.
- Cards and panels must keep their boundaries.
- Mobile/narrow-width layout should remain usable.
- Do not hide important user-facing errors completely.
- Do not dump full raw objects by default.

Add frontend tests, snapshot tests, or targeted unit tests if the existing test setup supports them.

At minimum, add reusable CSS utility classes or components for:

- safe code block
- safe log block
- safe long text
- compact diagnostic row
- collapsible debug details

---

# Task 8: Fix Chinese/English mixed UI problems

Audit the web UI for mixed-language text.

Goal:

If the selected UI language is Chinese, the normal UI should appear in Chinese.
If the selected UI language is English, the normal UI should appear in English.

Requirements:

- Do not mix Chinese and English labels in normal UI.
- Technical identifiers may remain English where appropriate, but they should not dominate the UI.
- Add missing translation keys.
- Remove hardcoded user-facing strings from frontend components where possible.
- Keep source names, company names, tickers, URLs, and technical IDs unchanged unless there is already a translation strategy.
- Use the global language setting consistently.
- Make language switching affect navigation, settings, source pages, monitor status, diagnostics, notifications preview, and error summaries.

Important distinction:

- Source content can be Chinese or English.
- UI language is separate from source language.
- LLM output language should follow configured output language.
- Internal code variable names must remain English.

Add or update tests that catch hardcoded UI strings if the existing framework supports it.

---

# Task 9: Make browser information concise and user-friendly

The browser UI should not feel like a raw developer console.

Improve the display model:

Normal user view should show:

- monitor status
- readiness status
- last run time
- enabled channels
- recent alerts
- source health summary
- source coverage summary
- candidate funnel summary
- latest important errors in plain language

Developer/debug view may show:

- raw JSON
- stack traces
- detailed source responses
- full rejection diagnostics
- raw config preview

Requirements:

- Hide developer-heavy detail behind collapsible sections.
- Summarize errors in plain language.
- Keep copy-to-clipboard for debug info if already supported or easy to add.
- Do not remove useful debugging capability.
- Make the default view suitable for a user who only wants to know: “Is it working? What did it find? What should I fix?”

---

# Task 10: UI visual polish

Improve UI readability without over-designing.

Focus areas:

- top bar contrast
- card spacing
- section hierarchy
- button labels
- status badges
- empty states
- warning/error states
- settings layout
- source package selection layout
- long-running monitor state display

Guidelines:

- Minimal modern style.
- Clear typography.
- Low visual noise.
- No huge raw text blocks in default view.
- No cramped panels.
- No unreadable light text on low-contrast backgrounds.
- Do not introduce heavy UI dependencies unless already used.

---

# Task 11: Settings UX for required keys/channels

Make settings clearer for users configuring the app.

The settings page should make obvious:

- which fields are required
- which fields are optional
- which notification channels are active
- whether LLM is configured
- whether Email is configured
- whether Telegram / Enterprise WeChat are configured, if supported
- where users can get required API keys or credentials

Do not hardcode secrets.

Use placeholder text, help text, or documentation links instead.

---

# Task 12: Tests and verification

Run or add tests for:

- GDELT keyword sanitization
- source package coverage
- root directory release cleanliness
- readiness diagnostics
- Yahoo/rate-limit classification
- candidate funnel rejection reasons
- frontend safe wrapping for long text if test framework supports it
- localization key coverage if test framework supports it
- config loading

Run:

```bash
python -m ruff check .
python -m black --check .
python -m pytest -q
python -m compileall src tests
python -c "from pathlib import Path; from src.config import load_config; load_config(Path('config.example.yaml'), load_env=False); print('config ok')"
```

If dependencies are missing, install them first:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

If the project has frontend package tooling, also run the relevant frontend checks, for example one of:

```bash
npm install
npm run lint
npm run test
npm run build
```

Only run commands that match the actual project structure.

---

# Task 13: Runtime smoke test

After tests pass, do a local smoke test if possible:

1. Load config from `config.example.yaml` or a local safe config.
2. Start the app locally.
3. Open the web UI.
4. Confirm no layout overflow on narrow and normal widths.
5. Switch UI language between Chinese and English.
6. Confirm labels change consistently.
7. Run one monitor cycle manually if safe.
8. Confirm source/readiness/candidate diagnostics are concise.
9. Confirm detailed raw diagnostics are hidden behind debug expanders.
10. Confirm notification settings still show Email as a valid channel.

Do not send real notifications unless the local config is intentionally set up for that.

---

# Non-goals

Do not do these in this pass:

- Do not add ordinary personal WeChat or QQ direct messaging unless already safely supported.
- Do not redesign the whole app.
- Do not replace the frontend framework.
- Do not rewrite the backend pipeline.
- Do not remove Structured Outputs.
- Do not hardcode OpenAI keys, Gmail credentials, passwords, or account IDs.
- Do not add paid data sources by default.
- Do not introduce scraping that violates website terms.
- Do not make the UI language logic depend on source language.

---

# Expected final report

At the end, provide a concise report with:

1. Files changed.
2. Runtime/source stability changes.
3. Web UI overflow fixes.
4. Localization fixes.
5. Tests added or updated.
6. Commands run and results.
7. Remaining known issues.
8. Whether the repo is ready for private GitHub push.
9. Exact suggested next commands for the user, for example:

```bash
git status
git add .
git commit -m "Stabilize monitoring runtime and web UI"
git push origin main
```
