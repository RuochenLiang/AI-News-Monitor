# Contributing

AI News Monitor welcomes focused fixes that improve local-first monitoring, source quality, notification reliability, documentation, and tests.

## Development Setup

```bash
./scripts/bootstrap_macos.sh
source "$HOME/.venvs/ai-news-monitor/bin/activate"
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall src tests
python -m ruff check .
python -m black --check .
```

Do not commit secrets, private prompts, runtime data, logs, SQLite databases, or generated release archives.

## Pull Request Checklist

- Keep source code English-only.
- Put Simplified Chinese user-facing text in `locales/zh-CN.json`, `README.zh-CN.md`, or `docs/zh-CN/`.
- Add or update tests for behavior changes.
- Update `README.md`, `README.zh-CN.md`, or docs when user workflows change.
- Verify GPL-3.0-only compatibility for new dependencies.
