# AI Signal Scout Portfolio Hardening Design

**Date:** 2026-09-13
**Status:** Approved for planning
**Branch:** `codex/portfolio-hardening`

## Purpose

Harden AI Signal Scout into truthful, public-safe proof of practical AI workflow design. The project must demonstrate a working English news-intelligence pipeline, automated scheduling, persistent recent-run state, deterministic selection rules, explicit failure behavior, and evidence that distinguishes offline tests from live external-service execution.

The project is a small portfolio system, not a production service. Documentation must describe what the code and verified runs actually support without claims such as “enterprise-ready,” “production-grade,” or “fully end-to-end tested.”

## Scope

This hardening covers:

- English output across prompts, validation, formatting, logs, tests, and documentation.
- Reliable RSS collection with explicit per-source health results.
- SQLite state restoration and saving across GitHub Actions runs.
- A single, testable candidate-selection and ranking contract.
- Current-run-only reporting.
- Honest separation of unit, offline integration, source-health, and live external-service verification.
- Fail-fast workflow outcomes and sanitized run evidence.
- Public repository and secret hygiene.
- README, architecture, and decision-record alignment.

The work does not include a web UI, a managed database, multilingual output, non-RSS scraping, LinkedIn copy, publication to LinkedIn, Telegram channel changes, or changes to any private project.

## Current-State Problems to Correct

The audited `main` revision `e4d61e9` has the following material mismatches:

- `data/signals.db` is ignored and is neither restored nor saved by GitHub Actions.
- The report path contains Persian prompts, labels, fallback text, function names, tests, and examples.
- The implemented path sends at most five candidates to Scout and stores at most three, while documentation promises a Top-5 report.
- `get_top_scored_signals(5)` is not scoped to the active run. Once persistence exists, old high scores could be repeatedly reported.
- The Sieve prompt describes one JSON object while the implementation expects a list of batch decisions.
- The Gemini client is created at import time, making keyless imports and unit tests fail.
- LLM, parsing, and Telegram failures can still leave the GitHub job successful.
- The script named as end-to-end validation simulates Sieve and Scout behavior and can report success without testing those services.
- Source URLs include confirmed 404 and automated-client failures.
- Architecture documentation refers to a stubbed collector, nonexistent packages, and a nonexistent reports table.
- Scheduled runs expose no sanitized artifact that proves source health, persistence restoration, report language, selection count, or delivery outcome.

## Target Architecture

```text
Curated RSS/Atom sources
  -> HTTP fetch + feed parse + freshness check
  -> SQLite URL deduplication
  -> source-balanced Sieve pool
  -> Gemini KEEP/DISCARD classification
  -> source-balanced Scout pool
  -> Gemini structured analysis
  -> deterministic weighted score + diversity selection
  -> English report validation and formatting
  -> optional Telegram delivery
  -> sanitized run-summary artifact
```

The production entry point remains `python -m src.main`. The root `main.py` becomes a thin compatibility wrapper or is removed if no supported invocation depends on it; it must not contain a second, divergent pipeline.

## Source Contract

### Curated source set

The maintained source configuration will contain nine endpoints:

| Source | Category | Decision |
| --- | --- | --- |
| OpenAI News | official | Use `https://openai.com/news/rss.xml` |
| Google DeepMind Blog | official | Keep the redirected healthy feed |
| Hugging Face Blog | official | Add `https://huggingface.co/blog/feed.xml` |
| arXiv cs.AI | research | Keep; an empty weekend feed is healthy |
| arXiv cs.CL | research | Keep; an empty weekend feed is healthy |
| TechCrunch AI | industry | Keep |
| The Verge AI | industry | Use `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml` |
| LangGraph releases | agents | Replace the blocked LangChain blog feed with `https://github.com/langchain-ai/langgraph/releases.atom` |
| OWASP GenAI Security Project | security | Use `https://genai.owasp.org/feed/` |

Anthropic is removed from the RSS configuration because no maintained official RSS endpoint was found during the audit. This limitation is documented rather than hidden or replaced with brittle HTML scraping.

### Fetch behavior

The collector will fetch bytes with `httpx`, a descriptive user agent, redirects enabled, and a 20-second timeout, then parse those bytes with `feedparser`. Non-2xx responses, request failures, malformed feeds, and missing entry links produce explicit source results rather than silent empty lists.

Each source result records only public-safe operational facts:

- source name;
- success or failure;
- entries parsed;
- recent entries considered;
- new rows inserted;
- duplicates skipped;
- a short sanitized error category when applicable.

Items older than seven days are excluded from the active run. Undated entries may be admitted because some valid feeds omit dates, but this is counted in diagnostics. Entries dated more than 24 hours in the future are rejected. Snippets sent to Gemini are limited to 1,500 characters.

A feed with a valid response and valid feed structure is healthy even when it contains zero entries, which accommodates arXiv’s weekend cadence. The pipeline continues through isolated source failures but fails the run if fewer than 60 percent of configured sources are healthy.

## Persistent State and Deduplication

SQLite remains the state store. The Actions workflow restores `data/signals.db` before execution and saves it only after tests and the live pipeline complete successfully.

State uses branch-scoped cache keys:

```text
ai-signal-scout-db-<os>-<ref>-<run-id>
```

Restore uses the same `<os>-<ref>` prefix so a run receives the most recent successful state for that branch. A concurrency group keyed by Git ref prevents two runs on the same branch from racing and saving divergent databases.

The cache is a rolling operational convenience, not permanent storage. GitHub may evict caches after inactivity or under repository storage pressure. Documentation will therefore claim persistent recent-run deduplication while the daily workflow remains active, not indefinite archival durability.

URL hashes remain the raw-signal primary key. `insert_raw_signal` returns whether a row was inserted, allowing collection to distinguish new items from duplicates. Failed pipeline runs do not save the partially updated database, so their candidates can be retried from the last successful cache.

The sanitized run summary records whether a database existed after the restore step, the starting and ending row counts, inserted rows, and duplicate skips. Cross-run evidence requires two distinct Actions run IDs where the second run reports restored state and at least one duplicate skip.

## Selection, Scoring, and Reporting Contract

The following constants define the professional default path:

```text
MAX_ITEM_AGE_DAYS = 7
SIEVE_INPUT_LIMIT = 50
SCOUT_INPUT_LIMIT = 15
REPORT_LIMIT = 5
MAX_PER_SOURCE_FIRST_PASS = 2
```

### Sieve input

All newly inserted current-run rows are eligible. Retrieval is deterministic: newest items first within each source, then round-robin across source priority. At most 50 items enter Sieve. The brittle title-keyword gate is removed because the source list is already AI-focused and the LLM stage is the intentional relevance filter.

Sieve processes batches of five and must return one validated decision for every candidate hash in a batch. Unknown hashes, duplicate decisions, missing decisions, invalid enum values, or malformed JSON fail the pipeline. KEEP candidates are ordered by Sieve confidence, then recency, and balanced by source for Scout input.

### Scout input and scoring

At most 15 KEEP candidates enter Scout. Scout must return structured English analysis for every supplied candidate, including:

- `url_hash`;
- `title`;
- `what_happened`;
- `why_it_matters`;
- `plain_english_explanation`;
- `x_discussion_angle`;
- six criterion scores from 0 through 100.

The source URL is never trusted from model output. The application restores it from the candidate mapped by `url_hash`.

Python computes the final score rather than trusting a model-generated total:

```text
capability_shift       25%
real_world_impact      20%
agent_relevance        20%
x_discussion_potential 15%
novelty                10%
source_quality         10%
```

Rank order is final score descending, publication time descending, then URL hash ascending for deterministic ties.

### Diversity and report size

Selection uses two passes:

1. Take ranked signals while allowing at most two from any organization.
2. If fewer than five were selected, fill remaining slots from the highest-ranked leftovers.

The report contains up to five signals from the active `run_id` only. It contains fewer when fewer than five valid current-run analyses exist. The product is therefore described as an “up-to-five daily brief,” not as a guaranteed five-item report.

When there are no new reportable signals, the run succeeds with status `no_new_report`, sends no Telegram message, and still saves successfully collected deduplication state.

## English Output Contract

English is the only production output language in this hardening. The formatter is named `format_report`. It produces one compact Telegram summary card designed to serve as LinkedIn-ready proof of the agent's work and to fit in a single standard desktop Telegram conversation screenshot without scrolling. Because viewport size and font scaling vary, the deterministic contract is a maximum of 15 logical lines and 1,000 visible characters, not a claim about every possible device.

The rendered Telegram card uses HTML-safe formatting so source URLs can appear as a clean `Source ↗` link instead of a long visible URL. Its exact visible structure is:

```text
AI SIGNAL SCOUT
AUTONOMOUS AI INTELLIGENCE BRIEF
2026-09-13 UTC · TOP 5
1 · 84.5/100 · Verified capability update
Why: The change affects practical agent workflows. · Source ↗
Live RSS → Gemini analysis → deterministic ranking → Telegram
```

Each additional signal repeats only the two item lines without spacer or separator lines. The count in `TOP N` reflects the actual number of current-run items. Titles and `Why` sentences are capped at 60 and 72 visible characters respectively, with word-boundary ellipsizing. Scores use one decimal place. `Source ↗` is a clickable link to the original HTTPS URL. The final provenance line makes the automated path visible in the screenshot without exposing implementation secrets or overstating the role of Gemini: collection and analysis are live, while score aggregation and ranking are deterministic Python behavior. The full `what_happened`, `why_it_matters`, `plain_english_explanation`, and `x_discussion_angle` values remain in SQLite for auditability; only the concise decision-useful view is delivered.

Prompts explicitly require English values even when an input title or snippet contains another language. Missing-field fallbacks are English and visible; missing required Scout fields normally fail validation rather than being silently filled.

Before delivery, the report validator checks the exact header, item, and provenance structure, nonempty report items, item count at or below five, the 15-line and 1,000-visible-character limits, valid HTTPS source links, and the absence of Arabic-script Unicode characters. This is a deterministic guard against the known Persian-output regression. It does not claim to perform general natural-language detection.

Telegram receives one HTML-formatted message with escaped dynamic text and a clickable source link for every item. The compact-card limit intentionally stays far below Telegram’s 4,096-character limit; a report that exceeds the one-frame contract fails validation rather than being split into multiple messages. Delivery logs do not print tokens, channel IDs, report text, source URLs, or Telegram message IDs.

## Failure Semantics

The live command exits nonzero when any of these occur:

- required Gemini credentials are missing;
- source health falls below the 60-percent threshold;
- a Gemini request exhausts retries or quota;
- Sieve or Scout output cannot be validated completely;
- eligible candidates exist but no valid Scout analyses are produced;
- English report validation fails;
- Telegram delivery is requested but credentials are missing or delivery fails;
- the sanitized evidence summary cannot be written.

No new signals and no KEEP candidates are normal successful outcomes. They are reported explicitly and do not masquerade as a delivered report.

The Gemini client is constructed lazily when a request is made. Importing the pipeline, running unit tests, offline validation, and source-health checks do not require a Gemini key.

## Verification Layers

### Unit tests

Built-in `unittest` remains the required test runner so the project does not add a test-framework dependency. Tests use temporary database files and cover:

- lazy Gemini initialization;
- source fetch-result classification and freshness behavior;
- insert-versus-duplicate accounting;
- deterministic balanced selection;
- complete Sieve and Scout response validation;
- weighted score calculation;
- two-pass diversity selection;
- current-run-only report queries;
- English formatter labels and regression guard;
- Telegram chunking and failure propagation;
- pipeline exit outcomes and sanitized summary fields.

All tests must be discoverable through `python -m unittest discover -s tests -v`.

### Offline integration validation

The misleading `e2e_validation.py` is replaced or renamed as an explicitly offline integration validation. It uses fixture feeds, a temporary SQLite database, deterministic fake LLM responses, and a recording Telegram adapter. Its output states that no external Gemini or Telegram service was contacted.

### Live source-health validation

A source-check command fetches every configured endpoint, prints a concise health table, and exits nonzero when the configured health threshold is missed. It never needs API keys.

### Live external-service verification

Only the production GitHub Actions workflow qualifies as live external-service verification because it fetches configured feeds, calls Gemini, formats the report, and optionally calls Telegram.

Manual dispatch accepts a `deliver_report` boolean. Scheduled runs always deliver when a valid report exists. Hardening verification uses:

1. a feature-branch run with delivery enabled to prove a real English Telegram send;
2. a second distinct feature-branch run with delivery disabled to prove state restoration and duplicate detection without sending a redundant message.

## Public-Safe Evidence

Each live workflow uploads `artifacts/run_summary.json` using a run-specific artifact name. The JSON may contain:

- schema version;
- pipeline run UUID;
- UTC timestamp;
- status;
- report language (`English`);
- source counts and sanitized per-source health;
- starting and ending database row counts;
- new and duplicate counts;
- Sieve, Scout, and report counts;
- state-restored boolean;
- delivery requested and delivery-success booleans.

It must not contain report text, article snippets, environment values, API keys, Telegram tokens, channel IDs, message IDs, local paths, private project names, or unrelated user information.

The workflow runs unit tests before the live pipeline, uses current Node 24-compatible official Action majors, sets least-privilege read permissions, declares a timeout, and uploads sanitized evidence even on failure when a summary exists. Database cache saving remains success-only.

## Documentation Contract

The README will explain:

- the actual architecture and up-to-five contract;
- the exact source categories and known Anthropic RSS limitation;
- the rolling cache persistence strategy and eviction limitation;
- local source checks, unit tests, offline integration validation, and live workflow validation;
- required secrets by name only;
- what is and is not automated;
- evidence artifact contents;
- honest known limitations.

`docs/architecture.md` will match the implemented modules and data flow. `docs/decisions.md` will amend the SQLite and GitHub Actions decisions to describe cache-backed recent-run persistence, deterministic scoring, diversity, and evidence boundaries. No nonexistent reports table or stubbed collector will remain in public documentation.

## Security and Repository Hygiene

- `.env`, local databases, virtual environments, and worktrees remain excluded.
- A safe `.env.example` may contain variable names and unmistakable placeholders only.
- Source examples use public URLs and nonfunctional identifiers.
- Secret-pattern scans cover the current tree and commit history before PR preparation.
- New commits use the repository owner’s GitHub `noreply` identity; existing history is not rewritten.
- The pre-existing personal email in commit metadata is reported as a history-hygiene note, not silently altered.
- No private project is named or referenced in repository content.

## Rollout and Evidence Gate

Implementation occurs only on `codex/portfolio-hardening`, in an isolated worktree, with test-first behavior changes and logically separated commits.

Before a pull request is prepared:

1. all unit tests pass locally on the available Python 3.14 runtime;
2. offline integration validation passes locally;
3. all configured sources pass the live health policy;
4. English/Persian regression scans pass;
5. dependency and secret scans show no exposed credential;
6. the branch is pushed;
7. the first live Actions run succeeds and Telegram delivery is reported successful;
8. the second live Actions run restores state and records duplicate skips;
9. uploaded summaries contain no sensitive fields;
10. README, architecture, decisions, and actual behavior agree.

The PR will not be merged without explicit user authorization in this chat.

## Known Limitations After Hardening

- GitHub Actions cache persistence can be evicted and is not an archival database guarantee.
- RSS-only collection omits important publishers that do not provide dependable feeds, including Anthropic at the time of this audit.
- Source outages can reduce a report below five items.
- Gemini judgments remain qualitative model outputs even though aggregation and ranking are deterministic.
- The pipeline analyzes feed titles and snippets, not full articles, so it must state when supplied detail is insufficient.
- A successful Telegram API response proves delivery acceptance but does not provide a public screenshot of a private channel.
- The system is single-workflow and SQLite-based; it is not designed for concurrent distributed processing.

## Acceptance Criteria

The hardening is ready for merge review only when evidence shows:

- the report is English end to end and passes the Arabic-script regression guard;
- a live branch workflow successfully sends a real Telegram report in English;
- a later branch workflow restores SQLite state and detects cross-run duplicates;
- the maintained source set meets the health threshold;
- selection, score computation, diversity, and up-to-five reporting match this contract;
- all discoverable unit tests and offline integration validation pass;
- live external validation is never represented by mocks;
- public documentation matches the implemented behavior and limitations;
- no secrets or private information are added;
- a sanitized evidence artifact exists for each verification run;
- the portfolio evidence bundle distinguishes safe, qualified, and unsupported claims.
