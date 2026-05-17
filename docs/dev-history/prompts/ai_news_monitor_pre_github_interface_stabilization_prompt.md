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
