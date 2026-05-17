# Architecture

AI News Monitor is a local desktop app with a background monitor loop and a lightweight local HTTP/SSE console.

## Main Components

- `src/app.py`: application startup and runtime-file preparation.
- `src/dependency_check.py`: lightweight runtime dependency checks with bootstrap guidance before the desktop UI starts.
- `src/scheduler.py`: background worker, lifecycle state, Run Once/E2E control actions, and local event server ownership.
- `src/monitor.py`: monitoring cycle, source fetches, ranking, LLM analysis, alert saving, notifications, E2E test fixture, pipeline funnel, and runtime status.
- `src/pipeline.py`: per-cycle funnel counts, rejection aggregation, zero-alert explanations, and concise summaries.
- `src/source_reliability.py`: source tier metadata, freshness states, intelligence-gap summaries, coverage quality, source package status, cache serialization helpers, and smart-polling backoff helpers.
- `src/sources/`: public source adapters and curated source library support.
- `src/storage.py`: SQLite persistence for articles, alerts, notification results, source runtime states, and local source cache/last-known-good data.
- `src/notifiers/`: email, Telegram, WeCom, relay webhook, and generic webhook delivery.
- `src/realtime.py`: local browser console, JSON status, `/health` liveness, `/readiness` readiness, Run Once/E2E control endpoint, and SSE stream.
- `src/ui/`: PySide launcher, settings, topics, logs, and dashboard.
- `locales/`: user-facing locale resources.

Runtime data lives outside the repository in the user's local app data directory.

## Reliability Flow

Each monitoring cycle loads persisted source state, checks per-source backoff, optionally reuses fresh source cache, fetches healthy due sources, updates last-known-good cache on success, and records failure/backoff state on error. Source states feed the dashboard, local JSON endpoints, intelligence-gap detection, and coverage-quality scoring.

Cached last-known-good entries are marked as cached/degraded and are not allowed to create new alerts unless the user explicitly enables cached alerting in configuration. This keeps diagnostics useful without sending stale alert spam.

## Operational Funnel

Every normal, Run Once, and E2E cycle records a funnel:

```text
source fetch -> language filter -> keyword filter -> dedupe -> ranking -> LLM -> alert -> notification
```

The funnel is serialized in `RuntimeStatus.pipeline_funnel` and includes top rejection reasons such as `no_keyword_match`, `duplicate`, `score_below_threshold`, `rate_limit`, `missing_notifier`, and `notification_failed`. E2E Test Mode uses a local test-only source and deterministic LLM analysis, then still uses normal alert persistence and configured or mocked notification paths.

## Local Console

The browser console is lightweight HTML/CSS/JS served by `src/realtime.py`. Primary cards show concise operator summaries; raw diagnostics and JSON are kept behind expandable details with copy controls. `/health` is server liveness only. `/readiness` combines monitor state, LLM readiness, notifier readiness, source coverage, critical gaps, last cycle status, and `can_send_alerts`.
