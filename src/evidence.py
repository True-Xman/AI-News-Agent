"""Public-safe run evidence models and serialization."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StorageCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_signals: int = 0
    processed_signals: int = 0


class SourceHealthEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_name: str
    healthy: bool
    entries_parsed: int = 0
    recent_entries: int = 0
    inserted: int = 0
    duplicates: int = 0
    undated: int = 0
    error_category: str | None = None


class PipelineSummary(BaseModel):
    """Strict allowlist for artifacts safe to publish from GitHub Actions."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    run_id: str
    status: Literal["running", "succeeded", "no_new_report", "failed"] = "running"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    report_language: Literal["English"] = "English"
    configured_sources: int = 0
    healthy_sources: int = 0
    source_health: list[SourceHealthEvidence] = Field(default_factory=list)
    database_rows_before: StorageCounts = Field(default_factory=StorageCounts)
    database_rows_after: StorageCounts = Field(default_factory=StorageCounts)
    new_signals: int = 0
    duplicates_skipped: int = 0
    sieve_evaluated: int = 0
    sieve_kept: int = 0
    sieve_discarded: int = 0
    scout_analyzed: int = 0
    scout_selected: int = 0
    report_signal_count: int = 0
    state_restored: bool = False
    delivery_requested: bool = False
    delivery_attempted: bool = False
    delivery_succeeded: bool = False
    failure_category: str | None = None


def write_run_summary(summary: PipelineSummary, path: str | Path) -> None:
    """Write only the validated allowlisted evidence payload."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(summary.model_dump_json(indent=2) + "\n", encoding="utf-8")
