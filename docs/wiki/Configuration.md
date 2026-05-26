# Configuration

Use the desktop app for normal configuration. Advanced users can edit the local runtime `.env` and `config.yaml` files directly.

## LLM Settings

Required fields:

- Provider or OpenAI-compatible base URL.
- Model name.
- API key.

Use Test LLM before starting monitoring. The API key is stored locally as `LLM_API_KEY`.

## Sources

Use public RSS/Atom feeds or supported public source candidates only. Do not add paywalled, login-only, private, or unauthorized scraped sources.

Source modes:

- `manual`: use only configured sources.
- `auto`: select sources from the built-in library based on the topic.
- `hybrid`: use configured sources first, then add relevant built-in sources.

## Topics

Each topic should include:

- A short name.
- A clear prompt.
- Keywords, entities, tickers, regions, or policy terms.
- Output language.
- Relevance and confidence thresholds.

Use Preview Source Selection to inspect which sources will be used before running a monitoring cycle.

## Notifications

Supported channels include email, Telegram, WeCom, WeChat relay, QQ relay, and generic webhook.

Run the channel Test button before starting monitoring. For Gmail, use an app password rather than the normal account password.
