# Troubleshooting

## The App Opens but Monitoring Is Not Ready

Open `http://127.0.0.1:8765/readiness`. Readiness summarizes monitor state, LLM readiness, notification readiness, source coverage, critical gaps, and last cycle status.

## LLM Test Fails

- `invalid_api_key`: create or copy a fresh key.
- `model_not_found`: use the exact model ID from the provider.
- `base_url_unreachable`: check the URL, VPN, proxy, firewall, and provider status.
- `unsupported_model_api`: use an OpenAI-compatible `/chat/completions` endpoint.

## No Alerts Are Sent

Check the Pipeline Funnel in the local console. Common blockers are no keyword match, duplicate articles, unsupported language, LLM rejection, relevance threshold, cooldown, rate limit, missing notifier, or notification failure.

## Source Test Fails

Only add public RSS/Atom feeds or supported public source candidates. If a source returns 429, non-JSON, empty feeds, or timeouts, use a different source package or lower polling frequency.

## Email Test Fails

For Gmail, use `smtp.gmail.com`, port `587`, STARTTLS, and a Gmail app password. The SMTP username and From address should usually be the same Gmail address.

## Build or Test Fails

Run:

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m black --check .
python -m pytest -q
python -m compileall src tests
```

GitHub Actions runs the same release-readiness gates on macOS and Windows.
