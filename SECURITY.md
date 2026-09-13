# Security Policy

## Reporting a vulnerability

Please use the repository's GitHub Security Advisory reporting flow for vulnerabilities. Do not open a public issue containing credentials, private channel identifiers, exploit details, or personal data.

## Credential handling

- Keep `GOOGLE_API_KEY`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHANNEL_ID` in local environment variables or GitHub Actions secrets.
- Copy `.env.example` to `.env` for local setup; never commit `.env` files.
- Rotate a credential immediately if it appears in a commit, log, screenshot, issue, or artifact.
- Do not paste private Telegram reports into public issues or pull requests.

The application constructs external clients only at request time. Telegram delivery logs exclude the Bot API URL, token, channel ID, report text, source URLs, and message ID. GitHub Actions uploads a strict, sanitized run-summary schema rather than the report itself.

## Scope and limitations

This repository is a small scheduled agent, not a security boundary for hostile multi-tenant workloads. It processes untrusted RSS text as data, limits stored snippets, validates model response shapes, restores source URLs from local records, and requires HTTPS report links. See [docs/architecture.md](docs/architecture.md) for trust boundaries and [docs/decisions.md](docs/decisions.md) for accepted limitations.
