# Architecture

## Runtime flow

```text
sources.yaml
  -> src.collectors.rss_collector
  -> src.storage (SQLite)
  -> src.intelligence.sieve (Gemini classification)
  -> src.intelligence.scout (Gemini analysis)
  -> deterministic Python score and diversity selection
  -> src.reporting.formatter
  -> optional src.reporting.telegram
  -> src.evidence run summary
```

`src.pipeline.run_pipeline` owns orchestration. `src.main` is the command-line adapter, and the root `main.py` delegates to the same entry point. This avoids two divergent pipelines.

## Components

### Configuration

`sources.yaml` contains nine ordered RSS or Atom endpoints. `src.config.config_loader` validates every source into a Pydantic `SourceItem`. Source priority determines stable collection and balancing order.

### Collection

`src.collectors.rss_collector` performs explicit HTTP GET requests with redirects, timeout, and a repository-identifying user agent. It parses response bytes with `feedparser`, categorizes HTTP/request/parse failures, and returns a `SourceCollectionResult` rather than a bare list.

Entries older than seven days or more than 24 hours in the future are excluded. Undated linked entries are accepted and counted. Snippets are converted to whitespace-normalized plain text and capped at 1,500 characters.

### Storage

`src.storage.database` resolves `SIGNALS_DB_PATH` at call time and creates idempotent schema migrations and indexes. The operational SQLite tables are:

- `raw_signals`: one row per global URL hash, original feed metadata, Sieve decision, and originating run ID;
- `processed_signals`: selected Scout analysis, deterministic score, source URL, and run ID;
- `sources`: reserved source metadata table retained by the existing schema.

Rendered reports have no dedicated storage table. They are transient and deliberately excluded from public artifacts.

Raw and KEEP retrieval is current-run-only, deterministic, limited, and round-robin balanced by normalized organization. Processed report queries require an active `run_id`.

### Sieve

`src.intelligence.sieve` retrieves up to 50 new current-run rows and sends batches of five to Gemini. The response must be a JSON array with exactly one Pydantic-validated decision per submitted URL hash. Missing, unknown, or duplicate hashes; malformed JSON; invalid decisions; and out-of-range values fail the pipeline before a batch is updated.

### Scout and ranking

`src.intelligence.scout` retrieves up to 15 source-balanced KEEP rows. Gemini returns evidence-grounded English analysis and six criterion scores for every supplied hash; it does not select the winners.

The application discards any model-provided source URL and restores URL, organization, timestamp, and original title from SQLite. Python calculates the 25/20/20/15/10/10 weighted score, sorts by score descending, publication time descending, then URL hash ascending, and applies a two-pass diversity rule. Only up to five selected rows are persisted for the active run.

### Reporting and delivery

`src.reporting.formatter` generates a single HTML-safe English Telegram card. Dynamic values are escaped, links must use HTTPS, the visible report is limited to 15 logical lines and 1,000 characters, and an Arabic-script regression guard runs before delivery.

`src.reporting.telegram` sends one HTML message with link previews disabled. It does not log the Bot API URL, token, channel ID, report body, source URLs, response description, or message ID. A requested delivery that Telegram does not accept is a pipeline failure.

### Orchestration and evidence

`src.pipeline` accepts dependencies for offline testing and chooses live defaults only at runtime. Outcomes are:

- `succeeded`: a current-run report was generated; requested delivery, if any, succeeded;
- `no_new_report`: no current-run report exists, so delivery was skipped;
- `failed`: an expected configuration, service, or response-contract error occurred.

`src.evidence.PipelineSummary` is a strict allowlist serialized to `artifacts/run_summary.json`. It contains only public-safe statuses and counts. Expected failures record the exception class, never its message.

## Trust boundaries

- Feed bodies and model responses are untrusted input.
- Source URLs come from configured feeds and must be HTTPS before reporting.
- Model JSON must pass strict shape, range, and exact-hash coverage checks.
- Final scoring and ranking do not trust a model-generated total.
- Credentials remain environment-only and are constructed into clients at request time.
- The report is sent to Telegram but never uploaded as a workflow artifact.

## Automation and persistence

GitHub Actions runs tests before the live command. A branch-scoped SQLite cache is restored before collection and saved under a unique run key only after success. Same-ref concurrency is serialized. The cache enables cross-run deduplication but can be evicted and is not an archival store.
