# Security Policy

## Supported Versions

This project is pre-1.0. Security fixes are applied to the default branch and the latest published release candidate when practical.

## Reporting a Vulnerability

Do not open a public issue containing secrets, credentials, private prompts, private source URLs, webhook URLs, Telegram tokens, chat IDs, or runtime files.

If GitHub Security Advisories are enabled for this repository, use a private advisory. Otherwise, open a minimal public issue that describes the affected area without secrets and ask the maintainer to arrange a private disclosure path.

## Secret Handling

The app stores local credentials in runtime files outside the source repository. Public examples should use `.env.example` and `config.example.yaml` only.
