# LLM Providers

AI News Monitor uses OpenAI-compatible chat completions for analysis, translation, and structured event reports.

## OpenAI

Set `llm.provider: openai` and put the key in the environment variable named by `api_key_env`.

In the desktop app, open Settings -> LLM, choose the primary provider, set optional fallback providers, and paste keys into the local key fields. Keys are written to the local `.env` file, not to source code.

```yaml
llm:
  provider: openai
  providers:
    openai:
      enabled: true
      api_key_env: OPENAI_API_KEY
      base_url: https://api.openai.com/v1
      model: gpt-4.1-mini
```

## DeepSeek

DeepSeek is configured as an OpenAI-compatible provider. It is disabled by default in the example config.

```yaml
llm:
  provider: deepseek
  fallback_providers:
    - openai
  providers:
    deepseek:
      enabled: true
      api_key_env: DEEPSEEK_API_KEY
      base_url: https://api.deepseek.com
      model: deepseek-v4-flash
```

Use `deepseek-v4-flash` for cost-sensitive monitoring. `deepseek-v4-pro` can be used when configured explicitly.

The Settings -> LLM tab exposes DeepSeek as a fallback/primary provider with model, timeout, retry, retry-backoff, and local API-key fields. Choose `deepseek` as the primary provider when you want the live monitor and Test LLM button to use DeepSeek first, and put `openai` in fallback providers when OpenAI should be tried after a DeepSeek failure.

The DeepSeek API docs list `deepseek-v4-flash` and `deepseek-v4-pro` as supported OpenAI-format model IDs. Legacy names `deepseek-chat` and `deepseek-reasoner` are compatibility aliases and are scheduled for deprecation on 2026-07-24.

- https://api-docs.deepseek.com/api/list-models
- https://api-docs.deepseek.com/quick_start/pricing
- https://api-docs.deepseek.com/updates

## Fallback

`fallback_providers` are tried in order after the primary provider fails. Each provider uses its configured `timeout_seconds`, `max_retries`, and `retry_backoff_seconds` for OpenAI-compatible HTTP calls. Unit tests use mocked providers; real API keys are not required in CI.

## Doctor Check

Run a local LLM configuration check without opening the desktop UI:

```bash
python -m ai_news_monitor doctor --check-llm
```

Use `--json` for machine-readable output.
