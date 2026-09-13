"""Dependency-injected orchestration with explicit success and failure outcomes."""

import json
import os
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .collectors.rss_collector import SourceCollectionResult, collect_rss
from .config.config_loader import SourceItem, load_sources
from .errors import ExternalServiceError, PipelineError
from .evidence import (
    PipelineSummary,
    SourceHealthEvidence,
    StorageCounts,
    write_run_summary,
)
from .intelligence.contracts import ScoutResult, SieveResult
from .intelligence.scout import run_scout
from .intelligence.sieve import run_sieve
from .reporting.formatter import format_report
from .reporting.telegram import TelegramClient
from .storage.database import init_db
from .storage.operations import get_storage_counts, get_top_scored_signals

SOURCE_HEALTH_THRESHOLD = 0.60
REPORT_LIMIT = 5


def _no_op_initialize() -> None:
    return None


def _zero_storage_counts() -> dict[str, int]:
    return {"raw_signals": 0, "processed_signals": 0}


@dataclass(frozen=True)
class PipelineDependencies:
    load_sources: Callable[[], list[SourceItem]]
    collect_source: Callable[[SourceItem, str], SourceCollectionResult]
    run_sieve: Callable[[str], Awaitable[SieveResult]]
    run_scout: Callable[[str], Awaitable[ScoutResult]]
    get_report_signals: Callable[[str, int], list[dict[str, Any]]]
    send_telegram: Callable[[str], bool]
    initialize_storage: Callable[[], None] = _no_op_initialize
    get_storage_counts: Callable[[], dict[str, int]] = _zero_storage_counts


def _load_report_signals(run_id: str, limit: int) -> list[dict[str, Any]]:
    return [json.loads(row[5]) for row in get_top_scored_signals(run_id, limit)]


def _send_telegram(report: str) -> bool:
    return TelegramClient().send_message(report)


def default_dependencies() -> PipelineDependencies:
    """Construct production adapters without contacting services at import time."""
    return PipelineDependencies(
        load_sources=load_sources,
        collect_source=collect_rss,
        run_sieve=run_sieve,
        run_scout=run_scout,
        get_report_signals=_load_report_signals,
        send_telegram=_send_telegram,
        initialize_storage=init_db,
        get_storage_counts=get_storage_counts,
    )


def _finish_summary(
    summary: PipelineSummary,
    dependencies: PipelineDependencies,
    summary_path: str | Path,
) -> None:
    summary.database_rows_after = StorageCounts(**dependencies.get_storage_counts())
    summary.completed_at = datetime.now(timezone.utc)
    write_run_summary(summary, summary_path)


async def run_pipeline(
    deliver_report: bool = True,
    summary_path: str | Path = "artifacts/run_summary.json",
    dependencies: PipelineDependencies | None = None,
) -> PipelineSummary:
    """Run the complete pipeline and always evidence expected outcomes."""
    active_dependencies = dependencies or default_dependencies()
    summary = PipelineSummary(
        run_id=str(uuid.uuid4()),
        delivery_requested=deliver_report,
        state_restored=os.environ.get("STATE_RESTORED", "").strip().lower() == "true",
    )

    try:
        active_dependencies.initialize_storage()
        summary.database_rows_before = StorageCounts(
            **active_dependencies.get_storage_counts()
        )

        sources = active_dependencies.load_sources()
        summary.configured_sources = len(sources)
        if not sources:
            raise ExternalServiceError("No RSS sources are configured")

        for source in sources:
            result = active_dependencies.collect_source(source, summary.run_id)
            summary.source_health.append(SourceHealthEvidence(**result.__dict__))
            summary.new_signals += result.inserted
            summary.duplicates_skipped += result.duplicates
            if result.healthy:
                summary.healthy_sources += 1

        if (
            summary.healthy_sources / summary.configured_sources
            < SOURCE_HEALTH_THRESHOLD
        ):
            raise ExternalServiceError(
                "Configured RSS source health is below 60 percent"
            )

        sieve_result = await active_dependencies.run_sieve(summary.run_id)
        summary.sieve_evaluated = sieve_result.evaluated
        summary.sieve_kept = sieve_result.kept
        summary.sieve_discarded = sieve_result.discarded

        scout_result = await active_dependencies.run_scout(summary.run_id)
        summary.scout_analyzed = scout_result.analyzed
        summary.scout_selected = scout_result.selected

        report_signals = active_dependencies.get_report_signals(
            summary.run_id,
            REPORT_LIMIT,
        )
        summary.report_signal_count = len(report_signals)
        if not report_signals:
            summary.status = "no_new_report"
            _finish_summary(summary, active_dependencies, summary_path)
            return summary

        report = format_report(report_signals, generated_at=summary.started_at)
        if deliver_report:
            summary.delivery_attempted = True
            if not active_dependencies.send_telegram(report):
                raise ExternalServiceError("Telegram did not accept the report")
            summary.delivery_succeeded = True

        summary.status = "succeeded"
        _finish_summary(summary, active_dependencies, summary_path)
        return summary
    except PipelineError as exc:
        summary.status = "failed"
        summary.failure_category = type(exc).__name__
        _finish_summary(summary, active_dependencies, summary_path)
        raise
