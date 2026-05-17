# Security Policy

## Supported Versions

The default branch is the supported development line until tagged releases are published.

## Reporting a Vulnerability

Do not open public issues containing secrets, private tokens, webhook URLs, or exploit details. Contact the project owner privately, then rotate any exposed credentials.

## Secret Handling

The app stores user credentials in local `.env` files and local configuration. Never commit:

- LLM API keys
- SMTP usernames or passwords
- Webhook URLs
- Telegram tokens or chat IDs
- Private user prompts
- Runtime databases or logs

Use `.env.example` and `config.example.yaml` for placeholders only.
