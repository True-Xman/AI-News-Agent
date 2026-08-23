# Architecture Decision Records (ADRs)

## ADR-001: Two-Stage AI Filtering
**Status**: Accepted
**Context**: 100+ raw signals per run are too many for a single deep analysis call (cost, latency, token limits).
**Decision**: Split into Stage 1 (low-cost noise filter) and Stage 2 (deep scoring).
**Consequences**: Adds complexity but dramatically reduces LLM costs and improves signal quality.

## ADR-002: SQLite for Persistence
**Status**: Accepted
**Context**: Need stateful deduplication across runs without managed DB costs.
**Decision**: Use SQLite (file-based, zero-config, free).
**Consequences**: Simple to deploy on GitHub Actions; not suitable for high-concurrency multi-process access (not needed for MVP).

## ADR-003: No LangChain / No Vector DB
**Status**: Accepted
**Context**: Avoid framework bloat and unnecessary infrastructure for MVP.
**Decision**: Direct LLM API calls (OpenAI-compatible) and standard Python libraries.
**Consequences**: More manual prompt engineering; full control over token usage and logic.

## ADR-004: Externalized Source Config (`sources.yaml`)
**Status**: Accepted
**Context**: Sources change frequently; hardcoding requires code changes.
**Decision**: YAML file loaded at runtime.
**Consequences**: New sources can be added without touching Python code.

## ADR-005: Scoring Formula Weights
**Status**: Accepted
**Context**: Need objective, repeatable ranking.
**Decision**: Fixed weights:
- Capability Shift: 25
- Real World Impact: 20
- Agent Relevance: 20
- X Discussion Potential: 15
- Novelty: 10
- Source Quality: 10
**Consequences**: Transparent scoring; anchor examples in prompt ensure calibration.

## ADR-006: Telegram as Delivery Channel
**Status**: Accepted
**Context**: Need private, real-time delivery with markdown support.
**Decision**: Telegram Bot API.
**Consequences**: Requires bot token and channel ID; free and reliable.

## ADR-007: GitHub Actions for Scheduling
**Status**: Accepted
**Context**: Zero-cost recurring execution without managing servers.
**Decision**: Daily cron workflow.
**Consequences**: 6-hour max runtime; IP rotation may trigger rate limits (mitigated by caching and polite scraping).