# AI Signal Scout

[![Daily Agent](https://github.com/True-Xman/AI-News-Agent/actions/workflows/daily_agent.yml/badge.svg)](https://github.com/True-Xman/AI-News-Agent/actions/workflows/daily_agent.yml)

AI Signal Scout is a scheduled AI-news agent that collects recent RSS and Atom entries, filters and analyzes them with Gemini, ranks them with deterministic Python logic, and can deliver a compact English brief to Telegram. Each report contains up to five current-run signals. It is designed as inspectable portfolio evidence, with explicit test boundaries and sanitized GitHub Actions artifacts.

## Architecture

```text
9 curated RSS/Atom feeds
  -> HTTP fetch, parsing, and freshness policy
  -> SQLite URL deduplication
  -> Gemini Sieve: KEEP or DISCARD
  -> Gemini Scout: structured analysis and six criterion scores
  -> Python weighted score and source-diverse Top N
  -> compact English HTML report
  -> optional Telegram delivery
  -> sanitized run-summary artifact
```

The live entry point is `python -m src.main`. External clients are created only when their live stage runs, so imports, unit tests, offline integration validation, and source checks require no Gemini or Telegram credentials. See [Architecture](docs/architecture.md) and [Decision Records](docs/decisions.md) for implementation details.

## Source set

The maintained source list is intentionally RSS-only and lives in `sources.yaml`.

| Priority | Source | Category |
| ---: | --- | --- |
| 1 | OpenAI News | Official |
| 2 | Google DeepMind Blog | Official |
| 3 | Hugging Face Blog | Official |
| 4 | arXiv cs.AI | Research |
| 5 | arXiv cs.CL | Research |
| 6 | TechCrunch AI | Industry |
| 7 | The Verge AI | Industry |
| 8 | LangGraph Releases | Agents |
| 9 | OWASP GenAI | Security |

`python scripts/check_sources.py` performs a live, credential-free health check. A pipeline run fails when fewer than 60 percent of configured sources are healthy. Empty but valid feeds remain healthy.

## Selection contract

- Accept entries published in the previous seven days and entries with no date; reject timestamps more than 24 hours in the future.
- Store at most 1,500 plain-text snippet characters and deduplicate globally by URL hash.
- Send up to 50 source-balanced current-run items to Sieve in batches of five.
- Require exactly one validated `KEEP` or `DISCARD` decision for every submitted hash.
- Send up to 15 source-balanced KEEP candidates to Scout and require one validated analysis for every hash.
- Compute final scores in Python: capability shift 25%, real-world impact 20%, agent relevance 20%, X discussion potential 15%, novelty 10%, and source quality 10%.
- Rank by score, publication time, and URL hash. Prefer no more than two items per organization in the first selection pass, then fill remaining slots up to five.
- Query only processed rows from the active run. No new reportable signal is a successful `no_new_report` outcome and causes no Telegram send.

The delivered card is English-only, contains at most 15 logical lines and 1,000 visible characters, and is optimized for one-frame Telegram Desktop screenshots. Each source URL is rendered as a compact clickable link. Full structured analysis remains in SQLite rather than crowding the public-facing brief.

## Automation

`.github/workflows/daily_agent.yml` runs every day at 17:30 UTC and supports manual dispatch. Scheduled runs request Telegram delivery; manual runs default to delivery disabled. The workflow:

1. installs pinned-major dependencies on Python 3.11;
2. runs all discoverable unit and offline integration tests;
3. restores branch-scoped SQLite state;
4. runs the live pipeline with repository secrets;
5. uploads sanitized run evidence even when an expected pipeline failure occurs;
6. saves SQLite state only after a successful job.

Same-ref runs are serialized to avoid concurrent writes. Workflow permissions are read-only for repository contents.

## Persistence and cache limitation

`data/signals.db` persists URL hashes, Sieve decisions, and selected Scout analyses. GitHub Actions restores the newest cache for the current branch and saves a unique cache entry for each successful run. This enables cross-run duplicate detection, but Actions cache is evictable and is not an archival database guarantee. Branches intentionally do not share deduplication state.

## Required environment names

Copy `.env.example` to `.env` for local live execution:

| Variable | Used for |
| --- | --- |
| `GOOGLE_API_KEY` | Live Gemini Sieve and Scout requests |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API authentication when delivery is enabled |
| `TELEGRAM_CHANNEL_ID` | Telegram delivery destination when delivery is enabled |

Keep real values in local environment variables or GitHub Actions secrets. See [Security Policy](SECURITY.md).

## Local commands

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/validate_offline.py
.\.venv\Scripts\python.exe scripts/check_sources.py
.\.venv\Scripts\python.exe -m src.main --deliver-report false
```

On macOS or Linux, replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.

## Verification levels

The evidence levels are deliberately separate:

- **Unit tests:** deterministic behavior for storage, source freshness, response contracts, scoring, selection, formatting, delivery payloads, orchestration, and workflow structure. No live service is contacted.
- **Offline integration:** `scripts/validate_offline.py` runs the real pipeline boundaries with a fixture feed, temporary SQLite database, deterministic model responses, and a recording delivery adapter. It explicitly states that Gemini and Telegram were not contacted.
- **Live source health:** `scripts/check_sources.py` fetches all configured feeds without credentials and enforces the 60-percent policy.
- **Live external-service run:** GitHub Actions fetches feeds, calls Gemini, optionally sends to Telegram, and publishes sanitized evidence. Only this level demonstrates external AI and delivery behavior.

Mocks and fixtures are never described as live end-to-end verification.

## Sanitized evidence

Every live workflow attempts to upload `run_summary.json` in a run-specific artifact. Its strict allowlist includes status, UTC timestamps, run ID, report language, source health and counts, database counts, Sieve/Scout/report counts, cache-restoration state, duplicate count, and delivery booleans.

The artifact excludes report text, article snippets, environment values, API keys, Telegram identifiers, message IDs, source URLs, local paths, and unrelated personal or project information.

## Known limitations

- RSS-only collection omits publishers without a dependable feed and analyzes titles and feed snippets rather than full articles.
- Gemini judgments are qualitative even though schema validation, weighted aggregation, tie-breaking, and final ranking are deterministic.
- Valid feeds can be empty, delayed, unavailable, or blocked temporarily, so a daily report may contain fewer than five items.
- A successful Telegram API response proves acceptance by Telegram; it does not publicly prove how a private channel rendered the message.
- SQLite and Actions cache suit a single serialized workflow, not concurrent distributed processing or archival retention.
- The Arabic-script regression guard targets the former language defect; it is not general language detection.
- One-frame fit is bounded by 15 logical lines and 1,000 visible characters, but physical fit still depends on window size, font scaling, and client UI.

## Safe portfolio claims

Supported by repository code and repeatable local checks:

- Built a two-stage, model-assisted RSS intelligence agent with strict structured-response validation.
- Implemented deterministic weighted ranking, source diversity, current-run isolation, and cross-run URL deduplication.
- Added a compact English Telegram output designed for a single screenshot frame.
- Separated unit, offline integration, live source-health, and live external-service evidence.
- Added fail-fast outcomes and public-safe workflow artifacts.

Claims about continuous uptime, guaranteed five-item reports, archival persistence, full-article fact checking, or public proof of private Telegram rendering are not supported.

## License

MIT
