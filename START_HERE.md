# Start Here

Use this file when you downloaded a release archive such as
`AI-News-Monitor-macOS.zip` or `AI-News-Monitor-Windows.zip`.

The intended flow is: unzip the archive, open the app, enter your own
settings in the desktop UI, run the built-in tests, then start monitoring.
Do not put API keys or passwords into the source repository.

## 1. Open the App

macOS:

- Unzip the archive.
- Open `AI News Monitor.app`.
- If macOS blocks an unsigned local build, right-click the app and choose
  Open, then confirm.

Windows:

- Unzip the archive.
- Open `AI News Monitor/AI News Monitor.exe`.

If you downloaded the GitHub source zip instead of a release archive, install
Python 3.11 and use the commands in `README.md` or `docs/INSTALL.md`.

## 2. Fill LLM Settings

Open Settings -> LLM Settings and fill:

- Provider: OpenAI, DeepSeek, or another OpenAI-compatible service.
- Base URL, for example `https://api.openai.com/v1`.
- Model name, for example `gpt-4.1-mini`.
- API key copied from your provider console.

Click Test LLM before continuing. The key is stored only in the local runtime
`.env` file.

## 3. Choose Sources

Open Settings -> Sources.

- Keep the starter source packages enabled, or enable the specific packages
  you need.
- Add custom RSS/Atom feeds only when they are public and allowed.
- Use Test Selected Source for any source you are unsure about.

## 4. Add Topics

Open Topics and add at least one enabled topic.

- Name: a short label.
- Prompt: what the monitor should track.
- Keywords: important names, companies, policy terms, or tickers.
- Output language: `en` or `zh-CN`.
- Source mode: use `hybrid` for the easiest first setup.

Use Preview Source Selection before running a real monitoring cycle.

## 5. Configure Notifications

Open Settings -> Notifications and configure at least one channel if you want
phone-friendly alerts.

- Email usually needs an app password, not your normal account password.
- Telegram needs a bot token and chat ID.
- Webhook and relay channels send notification content to that service, so
  review the provider's privacy and rate limits first.

Click the channel's Test button before starting monitoring. You can skip
notifications only if you plan to watch alerts locally in the app and browser
console.

## 6. Verify and Run

- Open the local console at `http://127.0.0.1:8765`.
- Use E2E Test to verify the local fetch -> LLM -> alert -> notification path.
- Use Run Once for a real monitoring cycle.
- When readiness is good, start normal monitoring and keep the computer awake.

Local runtime files are created outside the app bundle:

- macOS: `~/Library/Application Support/AI News Monitor/`
- Windows: `%APPDATA%/AI News Monitor/`
