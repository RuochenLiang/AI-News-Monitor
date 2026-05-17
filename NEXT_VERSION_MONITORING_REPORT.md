# Next Version Monitoring Report

Generated: 2026-05-17 after GitHub upload readiness finalization

## Executive Summary

The previously observed runtime issues have been converted into release-ready diagnostics, tests, and documentation. The project now has Run Once, E2E Test Mode, Pipeline Funnel, `/readiness`, source reliability/freshness/gaps, source package warnings, concise browser console summaries, GDELT/Yahoo failure classification, and Email From Address readiness validation.

The repository is intended to be safe for public GitHub upload after the final verification suite passed locally on 2026-05-17. Real credentials and runtime data are intentionally excluded.

## Current Operational Model

Local browser console:

```text
http://127.0.0.1:8765
```

Important endpoints:

```text
/health      server liveness only
/readiness   monitor readiness and can_send_alerts
/status      detailed runtime status
/events      SSE event stream
```

Browser console actions:

- Run Once: executes one real-source monitor cycle immediately.
- E2E Test: uses a local `[E2E TEST]` fixture and deterministic test LLM path to prove fetch -> candidate -> LLM -> alert -> notification flow.

## Issues From Earlier Runtime Observation And Current Status

### Full Alert Loop

Previous state: not proven because live sources produced no actionable alert.

Current state: E2E Test Mode proves the controlled alert pipeline with test-only data and mock/configured notification paths. Pipeline Funnel explains normal zero-alert cycles.

### GDELT

Previous state: production monitor query could fail with JSON parse errors while a small diagnostic query passed.

Current state: GDELT diagnostics test both production-shaped topic queries and a smoke query. Non-JSON responses, 429, timeout, TLS/network errors, long query, and malformed query shapes are classified without blindly calling `response.json()`.

### Yahoo Finance

Previous state: Yahoo RSS returned 429 and was shown as raw technical failure.

Current state: Yahoo 429 is classified as `api_rate_limited`, triggers source backoff, and is shown as a concise rate-limit status. Finance Starter contains alternative public finance sources.

### Email

Previous state: health could show ok while From Address was missing or invalid.

Current state: Email health, setup diagnostics, and send tests validate host, port, username, app password, explicit From Address, and recipients. From Address mismatch is a warning.

### Health vs Readiness

Previous state: `/health` could be misunderstood as full app health.

Current state: `/health` is liveness only. `/readiness` reports monitor, LLM, notifier, source coverage, critical gaps, last cycle status, and `can_send_alerts`.

### Paused State

Previous state: paused/running state could be missed.

Current state: status serialization includes pause reason and next cycle time, and the browser console shows a paused warning with resume/start/run controls.

### Source Packages

Previous state: empty package selection could make coverage critical without clear guidance.

Current state: source package status shows enabled state, source count, fresh count, failing count, last package test time, warnings, and recommended action.

### Browser Console

Previous state: primary cards could show raw JSON, raw errors, and long URLs.

Current state: primary cards show concise summaries, raw details are behind expanders, events are summarized and capped, and CSS uses overflow-safe rules.

## GitHub Upload Readiness

- GPL-3.0-only `LICENSE` exists.
- README language switching exists.
- AI disclosure exists and is referenced.
- Public docs exist: README, Chinese README, source guide, notification guide, install, architecture, roadmap, release checklist, contributing, security, changelog, code of conduct.
- `.gitignore` excludes secrets, runtime files, caches, logs, databases, builds, specs, and archives.
- Secret and runtime artifact scans are covered by release-readiness tests.
- Historical development prompts live under `docs/dev-history/prompts/` instead of cluttering the repository root.
- Generated local artifacts such as caches, `.DS_Store`, `.coverage`, and zip archives are not part of the upload candidate.
- Dependency/bootstrap helper gives missing dependency guidance.
- macOS Qt startup has a clean plugin-cache fallback for copied/quarantined PySide6 plugin files.
- GitHub Actions workflow files exist for CI, build, and release.

## Final Local Verification

- Ruff passed.
- Black check passed.
- Release-readiness tests: 17 passed.
- Target E2E/source reliability/interface/config tests: 45 passed.
- Full pytest: 102 passed.
- Coverage run: 102 passed, total coverage 66%.
- Compileall passed.
- `config.example.yaml` parse passed.
- Runtime dependency check passed.
- Workflow YAML parse passed.
- macOS shell script syntax passed.
- PowerShell syntax was not run locally because `pwsh` is not installed on this Mac; validate through GitHub Actions.

## Manual Validation Still Required

- Push to a private GitHub repository first and run GitHub Actions there.
- Validate Windows packaging on GitHub Actions or a Windows machine.
- Configure real user-owned credentials locally and run desktop tests.
- Run E2E Test Mode after notification setup to confirm delivery in the user's environment.
- Test live sources periodically because public feeds and APIs can change or rate-limit.
- Treat WeChat/QQ relay reliability as dependent on third-party services.
