# Architecture

## High-Level Flow

```
Sources → Raw Signals → Stage 1 (Noise Filter) → 15-20 Candidates → Stage 2 (Deep Analysis) → Top 5 Report → Telegram
```

## Component Breakdown

### 1. Sources (`src/config/sources.yaml`)
Externalized list of data sources (RSS, APIs) with priority and category.

### 2. Storage (`src/storage/`)
SQLite-backed persistence for:
- **sources**: Metadata about each feed.
- **raw_signals**: Unfiltered incoming signals (URL, title, snippet, timestamp).
- **processed_signals**: Post-filtering candidates with scores and analysis.
- **reports**: Generated daily intelligence reports.

### 3. Collection (`src/collectors/`)
Responsible for fetching raw signals from configured sources. Currently stubbed (no implementation).

### 4. Processing (`src/processing/`)
Contains the two-stage filtering logic:
- **Stage 1 (Sieve)**: Lightweight LLM call to discard low-value noise.
- **Stage 2 (Scout)**: Deep analysis assigning 0-100 scores and generating reports.

### 5. Intelligence (`src/intelligence/`)
Handles the scoring model and report generation:
- **Scoring**: Applies the weighted formula (Capability Shift, Real World Impact, etc.).
- **Report Generator**: Formats the Top 5 into X-friendly markdown.

### 6. Reporting (`src/reporting/`)
Manages the final output:
- Telegram message composition and sending.
- Message templating (ELI5, Why X Cares, etc.).

### 7. Models (`src/models/`)
Pydantic schemas for:
- `RawSignal` – Incoming news item.
- `ScoredSignal` – Post-filtering candidate with score and metadata.
- `DailyReport` – Structured intelligence report.

### 8. Config (`src/config/`)
Application configuration (database connection, Telegram bot token, etc.).

## Data Flow

1. **Ingest**: `collectors` pull new items from `sources.yaml`.
2. **Deduplicate**: Immediate URL-based check against `processed_signals`.
3. **Stage 1**: Send unique items to LLM for noise reduction.
4. **Stage 2**: Survivors undergo deep scoring and ranking.
5. **Report**: Top 5 are saved to `reports` and sent via Telegram.

## Scalability & Expansion

The modular design allows adding new sources, changing scoring weights, or extending the report template without rewriting core pipelines.