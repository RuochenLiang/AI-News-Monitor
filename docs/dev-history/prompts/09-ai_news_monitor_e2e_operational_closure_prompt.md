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
