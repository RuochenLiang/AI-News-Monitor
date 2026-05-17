# Roadmap

## Near Term

- Push the repository candidate to a private GitHub repository first and confirm CI, build, and release workflows pass before making it public.
- Validate the Windows artifact on GitHub Actions or a Windows runner.
- Run E2E Test Mode with a real user-owned notification channel after local credential setup.
- Continue refining source freshness, intelligence gaps, coverage quality, cache/backoff explanations, and source preset previews after the first release candidate.

## Later

- Add optional authenticated remote console mode.
- Add more source health probes, official-source discovery helpers, and optional gap warning notifications.
- Add import/export for topic and source presets.

The project should remain local-first and avoid collecting private runtime data.
