# Install and Run

## macOS

```bash
cd "/path/to/AI-News-Monitor"
./scripts/run_macos.sh
```

The script creates `~/.venvs/ai-news-monitor` when needed and starts `python main.py`.

## Windows

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Local Console

Open:

```text
http://127.0.0.1:8765
```

Use the desktop app for normal first-run setup: add the LLM key, choose source packages, create a topic, configure a notification channel, and test it before starting monitoring. The browser console is read-only and is intended for live monitoring status, source health, notification state, logs, and recent alerts. Advanced YAML and `.env` editing remain available in the local runtime directory.

Use LAN access only on trusted networks. Prefer SSH tunnels or an authenticated reverse proxy for remote access.

## Dependency Problems

Startup checks required runtime dependencies before opening the desktop UI. If a dependency such as `PySide6` or `feedparser` is missing, the app prints a message like:

```text
Missing required runtime dependencies:
- feedparser

Run: python -m pip install -r requirements.txt
```

Use the Python executable shown in that message, preferably inside a virtual environment. On macOS, rerun `./scripts/bootstrap_macos.sh` to recreate the managed environment.

## Local Verification

Before uploading to GitHub or publishing a release candidate, run:

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m black --check .
python -m pytest -q
python -m compileall src tests
```

Then start the app, open the local console, run E2E Test Mode, and confirm the Pipeline Funnel is visible.
