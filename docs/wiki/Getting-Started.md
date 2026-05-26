# Getting Started

## Release Archive Users

1. Download the macOS or Windows archive from GitHub Releases or GitHub Actions artifacts.
2. Unzip the archive.
3. Open `START_HERE.md` or `START_HERE.zh-CN.md`.
4. Open the app.
5. Fill LLM, source, topic, and notification settings in the desktop UI.
6. Run Test LLM, Test Selected Source, and notification Test.
7. Open `http://127.0.0.1:8765`.
8. Run E2E Test, then Run Once.
9. Start monitoring when readiness is good.

## Source Users

Install Python 3.11, then run:

```bash
cd "/path/to/AI-News-Monitor"
./scripts/run_macos.sh
```

On Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Runtime Files

The app creates local runtime files outside the source repository:

- macOS: `~/Library/Application Support/AI News Monitor/`
- Windows: `%APPDATA%/AI News Monitor/`

Store API keys and local settings there through the desktop app. Do not commit local runtime files.
