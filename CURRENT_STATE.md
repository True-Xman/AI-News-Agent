# Current State - AI News Agent

## Working

- RSS Collector
- run_id pipeline isolation
- Sieve filtering
- Scout scoring
- Persian report generation

## Current Issues

- Fixing source_url propagation in Scout/reporting
- Reducing LLM token consumption

## Architecture Rules

Do not modify:
- Gemini client architecture
- Database schema
- run_id architecture

## Development Rules

Before changing code:

1. Inspect only relevant files.
2. Do not scan the whole repository.
3. Explain root cause before editing.
4. Make minimal changes.