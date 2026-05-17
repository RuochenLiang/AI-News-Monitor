# Phase Verification Prompt

## Objective

Verify that the AI News Monitor application has implemented all mandatory features from the next phase specification and runs successfully on your machine. Perform the following tasks in sequence and record your observations.

1. **Environment Setup**
   - Ensure your working directory contains the latest source code for the AI News Monitor and the updated specification file.
   - Confirm that `.env` and `config.yaml` files exist and include valid API keys for the LLM and translation services, as well as dummy notification endpoints for Email and each chat channel (WeCom, Telegram, WeChat/QQ via ServerChan if supported).  If any secrets are missing, note the issue and stop.

2. **Build and Run**
   - Use the provided packaging script or instructions to build the application for your platform (Windows or macOS).  Capture any build warnings or errors.
   - Launch the built application.  Confirm that it starts correctly and opens the local UI at `http://localhost:<port>`.

3. **Functional Checks**
   - **Multilingual Input:** Create a monitoring rule with keywords in both Chinese and English.  Verify that news items from Chinese and English sources are fetched and displayed.  Translation should occur automatically when the language of the article differs from the selected UI language.
   - **Language Toggle:** Use the language toggle in the settings to switch between Chinese and English.  Ensure that all interface text, notifications, and logs update instantly and consistently to the selected language.
   - **Notifications:** Configure each available notifier (Email, WeCom, Telegram, WeChat/QQ).  Use dummy addresses or webhooks where necessary.  Send a test notification through each channel and verify that the status indicator reports success and records the time of the last message.
   - **UI Design:** Observe the UI aesthetics.  Confirm that it follows the minimalist Apple‑inspired design with generous white space, clean fonts, a restrained colour palette and subtle animations.  Interactions such as opening dialogs or expanding configuration panels should be smooth and non‑blocking.
   - **Real‑Time Updates:** Ensure that new articles appear in the UI without needing to refresh the page, using SSE or WebSockets.  Watch the live indicator or notification banner for updates.

4. **Stability Checks**
   - Let the application run for at least five minutes.  Observe whether memory usage grows abnormally or whether any errors appear in the log.  Check that all notifier channels remain connected and attempt automatic reconnection if a connection drops.
   - Test the retry logic by intentionally disconnecting one notification service (e.g. disable internet on the computer) and then re‑enable it.  Confirm that notifications resume automatically.

5. **Summary**
   - Provide a detailed summary indicating which features are fully functional, partially implemented, or missing.  Include observations about build quality, UI consistency, translation accuracy, notifier stability and real‑time updates.
   - Highlight any bugs, performance issues or design discrepancies you discovered.
   - Suggest concrete next steps to fix defects or finish incomplete features.

## Completion

When all checks are complete, output your findings in a structured report using the above “Summary” format.  Mark the task done once you have verified the phase completion.
