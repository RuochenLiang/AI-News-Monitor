# Install and Run

## Release Archive

If you downloaded `AI-News-Monitor-macOS.zip` or
`AI-News-Monitor-Windows.zip`, start with `START_HERE.md` or
`START_HERE.zh-CN.md` in the unzipped folder.

The release flow is:

1. Unzip the archive.
2. Open the app.
3. Fill LLM, source, topic, and notification settings in the desktop UI.
4. Run Test LLM, Test Selected Source, and notification Test.
5. Open `http://127.0.0.1:8765`, run E2E Test, then Run Once.
6. Start monitoring when readiness is good.

Local runtime files are created automatically:

- macOS: `~/Library/Application Support/AI News Monitor/`
- Windows: `%APPDATA%/AI News Monitor/`

Do not edit API keys into the repository or app bundle. Use the desktop app
settings; secrets are stored in the local runtime `.env` file.

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
