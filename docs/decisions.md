# Architecture Decision Records

## ADR-001: Use two model-assisted stages

**Status:** Accepted

**Decision:** Sieve classifies up to 50 fresh candidates in batches of five. Scout analyzes up to 15 KEEP candidates. Both stages require exact URL-hash coverage and strict Pydantic validation.

**Trade-off:** Two calls and two contracts add code, but reduce deep-analysis volume and make incomplete model output fail visibly.

## ADR-002: Compute final scores in Python

**Status:** Accepted

**Decision:** Gemini supplies six 0–100 criterion values. Python applies fixed 25/20/20/15/10/10 weights, deterministic tie-breaking, and two-pass source diversity.

**Trade-off:** Criteria remain qualitative model judgments, but aggregation and ranking are inspectable and repeatable.

## ADR-003: Use SQLite with Actions cache persistence

**Status:** Accepted

**Decision:** Store URL hashes and analysis in `data/signals.db`. Restore the newest same-branch cache and save a unique cache entry only after a successful workflow.

**Trade-off:** This is inexpensive and supports cross-run deduplication, but cache eviction means it is not archival persistence. Same-ref runs must remain serialized.

## ADR-004: Maintain an RSS-only source set

**Status:** Accepted

**Decision:** Use nine audited RSS or Atom endpoints and a credential-free health command. Exclude publishers without a dependable feed instead of adding fragile HTML scraping.

**Trade-off:** Coverage is narrower and limited to feed titles and snippets, but collection remains transparent, testable, and low-maintenance.

## ADR-005: Deliver a compact English Telegram card

**Status:** Accepted

**Decision:** Deliver one HTML-safe message with up to five items, clickable source labels, at most 15 logical lines, at most 1,000 visible characters, and an explicit pipeline provenance line.

**Trade-off:** The screenshot-ready brief omits full analysis fields, which remain auditable in SQLite. Physical one-frame fit still varies with Telegram viewport and font scaling.

## ADR-006: Publish sanitized workflow evidence

**Status:** Accepted

**Decision:** Upload a run-specific strict-schema summary containing statuses, counts, source health, cache restoration, and delivery booleans. Never upload report text, snippets, credentials, Telegram identifiers, message IDs, source URLs, or local paths.

**Trade-off:** Public evidence can prove pipeline state and Telegram API acceptance, but cannot prove the rendered contents of a private Telegram channel.

## ADR-007: Separate verification levels

**Status:** Accepted

**Decision:** Describe unit tests, fixture-driven offline integration, live RSS health, and live GitHub Actions external-service runs as distinct evidence levels.

**Trade-off:** Portfolio claims are more qualified, but they remain reproducible and do not present mocks as live behavior.

## ADR-008: Fail expected operational errors explicitly

**Status:** Accepted

**Decision:** Missing live credentials, low source health, exhausted Gemini requests, invalid model output, invalid English report boundaries, requested Telegram failure, and evidence serialization failure produce a nonzero-capable error. Zero new signals remains a successful `no_new_report` state.

**Trade-off:** Scheduled runs may fail more visibly during external outages, which is preferable to false success.
