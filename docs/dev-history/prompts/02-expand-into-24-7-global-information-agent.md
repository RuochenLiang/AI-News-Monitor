# AI News Monitor — 24/7 Global Information Agent Next Phase Prompt

This file contains the high-level specification for the **AI News Monitor - Next Phase** project. The goal is to evolve the existing news monitor into a lightweight yet powerful tool that can gather real-time information from around the globe, filter it intelligently, and deliver it to the user through email or messaging apps. Analysis remains the user's responsibility; the monitor focuses on timely collection and high-quality surfacing of relevant articles.

## Purpose

Transform the existing AI‑powered news monitor into a **24/7 global information agent** that:

* Continuously fetches articles from a wide array of instantaneous news sources around the world and matches them against user‑provided prompts or keywords.
* Prioritises **quality over quantity** through robust relevance ranking, deduplication and source reliability scoring.  Information volume may be large, but only the most pertinent articles should be forwarded.
* Supports **bias awareness** by comparing multiple sources covering the same event and highlighting differences in tone or ownership.  Where possible, provide a short note about source bias or context without making editorial judgements.
* Offers **multilingual support** by translating and summarising non‑English articles (initially Chinese ↔ English) so that users receive coherent content regardless of source language.
* Delivers notifications instantly via **email and optional chat channels** (WeCom/Telegram).  Users can edit where the alerts go and adjust parameters at runtime through the configuration UI.
* Runs primarily as a **self‑hosted server** on the user’s computer for local processing and privacy.  Deployment should be simple: unzip and run the binary on Windows or macOS; no container orchestration required for everyday use.
* Presents a **modern, Apple‑style minimalist UI** that is fast, uncluttered and stylish, using generous whitespace, clean typography and a restrained colour palette.  Interface elements must not block content and should load quickly.

## Key Features and Requirements

1. **Advanced Filtering & Prioritisation** (adopt suggestion 1)
   * Implement a relevance scoring system that considers keyword matches, publication time, source reliability and recency.  Rank articles before delivery to keep only the most relevant.
   * Provide an adjustable threshold in the configuration UI so users can choose how strict the filter is.  Offer sensible defaults.

2. **Cross‑Source & Bias Analysis** (adopt suggestion 2)
   * For a given news event, gather reports from multiple sources and group them.  Use heuristics or AI to detect when stories refer to the same event.
   * Generate a short comparative summary that highlights differing viewpoints and notes potential bias or ownership context.  Present this alongside links to the original articles.
   * Allow the user to enable/disable bias analysis and choose whether to see only the best single source or a cluster of sources.

3. **Multilingual Translation & Summarisation** (adopt suggestion 4)
   * Integrate translation for languages not matching the user’s preferred language (default to Chinese and English).  Translate titles and summaries while preserving the original text.
   * Use the same LLM for summarising the translated content into 1–2 sentences.  Do not perform deeper analysis; simply condense and translate.
   * Allow the user to configure which languages to translate and the target language.

4. **Real‑Time Updates via SSE/WebSockets** (adopt suggestion 5)
   * Implement a server‑sent events (SSE) or WebSocket mechanism in the desktop app.  When new articles arrive or are enriched, push them to the UI without requiring a page reload.
   * Add a “live” banner or notification indicator in the UI when new items appear.
   * Ensure the local server remains efficient even with persistent connections.

5. **Technical & Deployment Optimisation** (adopt suggestion 12)
   * Audit the codebase to eliminate unnecessary dependencies and reduce memory footprint.  Remove unused functions, avoid artificial delays and profile the critical paths.
   * Package the application with PyInstaller for both Windows and macOS.  Create a standalone binary that includes all required libraries and a minimal Python runtime.
   * Update GitHub Actions workflows to build these binaries automatically.  Supply `.env.example` and `config.example.yaml` files for easy configuration.  Ensure `.env`, `config.yaml`, `logs` and `data` directories are excluded from version control.
   * Avoid hard‑coding any API keys, email addresses or chat tokens.  All secrets must be loaded from environment variables or through the configuration UI.

6. **Language Support and Unified Output**
   * The application must recognise **Chinese and English** input sources only.  Do not monitor or translate articles from other languages.  Users may enter prompts in either Chinese or English; the monitor must handle both natively.
   * Provide a **global language toggle** (Chinese ↔ English) that affects the entire application at both the system and scripting levels.  Selecting a language must immediately update the UI, all logs, summaries and notifications without restarting.  When a language is selected, ensure that every piece of output—including article summaries, error messages, configuration labels and help text—is presented **consistently** in that language.
   * Offer a simple switch in the settings panel for users to choose their preferred language.  The toggle should be clearly labelled in both languages (e.g. “语言 / Language”) so that switching from one to the other is intuitive.  The default can follow the system locale.

7. **Expanded Chat Notifiers**
   * Beyond the existing email, WeCom and Telegram channels, **add support for ordinary WeChat and QQ** where feasible.  If there is no official API for direct push, integrate via trusted third‑party relay services (such as Server酱、ServerChan 或 Chanify) that forward notifications into personal WeChat/QQ accounts.  Provide clear setup instructions, warn about any reliability or privacy trade‑offs and allow the user to enable/disable this feature.
   * **Restructure the notifications settings UI** to emphasise clarity and reduce cognitive load: break the page into separate sections for each channel (Email, WeCom, Telegram, WeChat, QQ, Webhook, etc.).  Within each section, show only the minimum required fields (e.g. address, token, webhook URL) and hide advanced options behind an “Advanced” toggle.  Use descriptive labels in the selected language.
   * Add form validation so that channels cannot be enabled until required fields are completed.  Display real‑time feedback on whether the system can connect to each service (Connected / Error / Disconnected) along with the last successful message time, so users can assess **long‑term stability**.

8. **Natural Animations and Modern Dialogs**
   * Enhance the UI with subtle, non‑intrusive animations: e.g. fade transitions when changing pages, smooth expansion/collapse of configuration panels and gentle notifications when new articles arrive.  Animations must never block user actions or slow down the interface.
   * Use modern dialog components for confirmation, errors and status messages.  Dialogs should match the minimalist theme and support both Chinese and English text.
   * Ensure that all interaction elements (buttons, toggles, forms) are keyboard navigable and accessible.

9. **Port and Service Stability**
   * Design the notification and API endpoints (SMTP, WeCom/Telegram/WeChat/QQ webhooks, translation services) to handle reconnections and failures gracefully.  Implement retry logic with exponential backoff when sending notifications or making API calls.
   * Expose health checks for each external service so that the server can report whether a channel is currently operational.  Display this information in the configuration UI and log persistent failures.

10. **Minimalist UI & Local Control**
   * **Rebuild the interface** in the spirit of Apple design: large headings, generous whitespace, crisp sans‑serif fonts and a restrained colour palette with a single accent colour.  Keep the aesthetic lightweight and modern, avoid overcrowding or unnecessary decoration.
   * Ensure the layout is responsive and comfortable on desktops and laptops (primary target environment).  Components must load quickly, react to user input without lag and avoid heavy animations that slow down weaker machines.
   * Provide a **comprehensive dashboard** where the user can monitor the system’s status: total articles processed, last fetch time, queue length, connection health for each notifier, and log messages.  Users should be able to **pause, resume and stop** the monitoring process, and view immediate feedback on their actions.
   * Create intuitive **configuration panels** that allow users to:
     * View and edit where information is sent (email addresses, chat accounts).  Adding or removing channels should be as simple as filling out a short form.
     * Input or update API keys for the LLM and translation services, and choose which model or translation engine to use.
     * Define or modify keywords, prompts and other monitoring parameters without editing files by hand.
     * Adjust the relevance threshold, select which languages to translate, enable/disable bias comparisons and specify how often to refresh sources.
   * Provide bilingual interface text (Chinese and English) across all views, ensuring that changing the language toggle updates the entire UI, including all control labels, help text and error messages.
   * Show complete feedback for each operation (e.g. when a new article is matched, display summary, source, and processing time) and allow the server operator to view raw logs if deeper debugging is needed.

11. **Global Source Integration & Quality Assurance**
   * Expand the list of news sources beyond the current defaults (GDELT, Google News RSS, Yahoo Finance).  Use additional free APIs or public RSS/Atom feeds to increase coverage.  Maintain a curated list of reliable sources and allow users to add custom feeds via the UI.
   * Deduplicate articles across sources using URL, title similarity and content fingerprinting.  Ensure that duplicates from different sources are not sent multiple times.
   * Fetch metadata for each source (language, reliability score).  Use reliability scores to down‑rank or exclude low‑trust outlets.

12. **Easy Deployment & Operation**
   * Default running mode should be as a local server that starts when the user launches the binary.  Provide a system tray icon or status indicator.
   * Users should access the UI via a local browser at `http://localhost:PORT`.  Optionally allow remote access via LAN with proper security and authentication.
   * For those deploying on a remote VPS, provide a simple set‑up guide: install dependencies, configure environment, run the binary or container.

## Implementation Steps

1. **Planning & Analysis**
   * Review the existing codebase to understand the current architecture, data flow and dependencies.
   * Identify modules that need expansion (e.g. source fetchers, notifier engines, UI components).

2. **Source Expansion & Ranking**
   * Create new fetcher classes for additional RSS/Atom feeds and public news APIs.
   * Implement deduplication and reliability scoring for each fetched article.  Provide a function to compute a combined relevance score.

3. **Bias Analysis Module**
   * Develop a grouping algorithm to cluster articles referring to the same event using title similarity or entity extraction.
   * For each cluster, generate a short comparative summary (use LLM or templated heuristics).  Annotate sources with ownership or known bias when available.

4. **Translation & Summarisation**
   * Integrate a translation service (e.g. OpenAI, HuggingFace translation models) to translate titles and summaries into the user’s preferred language.  Preserve original text for reference.
   * Use the existing LLM client to summarise translated content.  Ensure both translation and summary are optional and configurable.

5. **Real‑Time Delivery & UI Enhancements**
   * Implement SSE/WebSocket endpoints on the backend.  Update the frontend to open a persistent connection and append new articles to the list as they arrive.
   * Add UI controls to adjust real‑time update preferences (e.g. enable/disable, update frequency).
   * Apply the minimalist design guidelines throughout the interface.  Replace heavy components with lightweight alternatives; remove unused icons or animations.

6. **Configuration & Secrets Handling**
   * Extend the configuration schema to include new settings: relevance threshold, languages, bias analysis toggle, additional sources.
   * Build forms in the UI for editing configuration.  Save changes to `config.yaml` or another persistent store.  Do not require a restart to apply most changes.
   * Ensure all secrets are stored only in `.env` or via the UI’s secret input fields.  Never commit sensitive data to the repository.

7. **Testing & Packaging**
   * Write unit tests for new modules: source deduplication, relevance scoring, bias grouping, translation pipeline and SSE handler.
   * Use continuous integration to run tests on each commit.
   * Update packaging scripts to include the new dependencies.  Test that the built binaries run on Windows 10/11 and macOS (Intel & M‑series).
   * Provide an updated `README.md` detailing the new features, configuration options, installation steps and usage instructions.

## Completion Criteria

The Codex agent should consider this implementation complete when:

* All new modules and UI elements described above are present and functional.
* The application can fetch articles from multiple global sources, deduplicate them, rank them by relevance and deliver notifications in real time.
* Multilingual translation and bias comparisons work as expected, and users can toggle these features.
* The UI adopts the minimalist design, and users can configure sources, destinations, API keys and parameters on the fly.
* Packaging scripts produce working binaries for both Windows and macOS, with `.env.example` and `config.example.yaml` provided.
* Automated tests pass and no secrets are hard‑coded in the codebase.
