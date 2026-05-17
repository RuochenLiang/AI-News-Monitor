# Notification Guide

AI News Monitor stores alerts locally first, then sends notifications through enabled channels. Fast Alert mode is the default for all channels.

## Fast Alert vs Full Analysis

`alerts.default_mode: "fast"` sends:

- Title and translated title when available
- Source and published time
- Original URL
- Short summary
- Match reason and matched keywords/entities
- Source reliability/context
- Cluster ID when available
- Multi-source confirmation context when available
- Why the item was selected

`alerts.default_mode: "full_analysis"` also includes deeper LLM fields such as why-it-matters, market-watch suggestions, bullish/bearish scenarios, risk notes, and uncertainty notes.

## Fallback Routing

Notification fallback is controlled by:

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

When fallback is enabled, the app retries a failing channel with exponential backoff, then moves to the next enabled channel until one succeeds. If fallback is disabled, the app attempts every enabled channel.

## Required Information

- LLM: API key, base URL, model name.
- Email: SMTP host/port/TLS, username, app password, from address, recipients.
- Telegram: BotFather token and chat ID.
- WeCom: group robot webhook URL.
- WeChat relay: ServerChan or Chanify URL. Third-party relay services can see notification content.
- QQ relay: Qmsg or compatible relay URL. Third-party relay services can see notification content.
- Generic webhook: URL, optional method, headers, and body template.

The Settings page provides help buttons for each channel and a test button for every notification channel. The app prevents enabling a channel from the UI when required local fields are empty.

## Gmail / SMTP Setup

For Gmail, use:

- SMTP host: `smtp.gmail.com`
- SMTP port: `587`
- STARTTLS: enabled
- SMTP username: the sender Gmail address
- SMTP password: a Gmail app password
- From address: usually the same sender Gmail address
- Recipients: the email addresses that should receive alerts

Gmail app passwords require 2-step verification. Organization-managed Google Workspace accounts may disable app passwords or block SMTP; in that case ask the administrator or use another notification channel. If port `587` is blocked by a network or VPN, the test may report `smtp_connection_timeout`.

Email health, setup diagnostics, and send tests all validate the same required fields. `from_address` is required and must be a valid email address. If it differs from the SMTP username, the app allows it but shows a warning because many SMTP providers reject aliases that are not explicitly approved.

## Notification Diagnostics

Every notification test returns a structured result:

- `ok`: whether the test message was sent.
- `category`: standard failure category.
- `missing_fields`: fields that must be filled before the channel can work.
- `suggested_fix`: next action to try.
- `technical_detail`: redacted provider or network detail.

The browser console summarizes notification readiness first and keeps detailed diagnostic fields behind expandable details. If an alert is saved but no notifier is ready, the pipeline funnel reports `missing_notifier`. If delivery fails, it reports `notification_failed` and the alert remains stored locally.

Common categories:

- `missing_required_field`: fill all required fields and save settings.
- `invalid_url`: paste a full HTTP/HTTPS webhook URL.
- `invalid_email_address`: fix sender or recipient address formatting.
- `smtp_auth_failed`: use a provider app password, not the normal login password.
- `smtp_starttls_failed`: check port 587 and STARTTLS.
- `smtp_sender_rejected`: make From match the authenticated sender or allowed alias.
- `smtp_recipient_rejected`: check recipient addresses and provider policy.
- `smtp_provider_blocked`: check provider security alerts or organization policy.
- `webhook_unreachable`, `webhook_http_error`, `webhook_auth_failed`: regenerate or verify the webhook URL/token and provider status.

## Secrets

Secrets go in `.env`, not in source code:

```text
LLM_API_KEY=...
EMAIL_APP_PASSWORD=...
TELEGRAM_BOT_TOKEN=...
```

Never send your real `.env`, `config.yaml`, logs, or database to someone else.
