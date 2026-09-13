"""Fixture-driven integration validation with no external service calls."""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.rss_collector import collect_rss
from src.config.config_loader import SourceItem
from src.intelligence.scout import run_scout
from src.intelligence.sieve import run_sieve
from src.pipeline import PipelineDependencies, run_pipeline
from src.storage.database import init_db
from src.storage.operations import get_storage_counts, get_top_scored_signals

FIXTURE_BYTES = (PROJECT_ROOT / "tests" / "fixtures" / "sample_feed.xml").read_bytes()
FIXED_NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def _candidate_list(prompt: str) -> list[dict]:
    return json.loads(prompt.rsplit("Candidates:\n", 1)[1])


async def _run_validation() -> None:
    print("OFFLINE INTEGRATION VALIDATION — SIMULATED EXTERNAL SERVICES")
    with tempfile.TemporaryDirectory() as directory:
        previous_db_path = os.environ.get("SIGNALS_DB_PATH")
        os.environ["SIGNALS_DB_PATH"] = str(Path(directory, "signals.db"))
        deliveries: list[str] = []
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=FIXTURE_BYTES)
        )

        try:
            with httpx.Client(transport=transport) as client:
                source = SourceItem(
                    name="Offline Fixture",
                    url="https://fixture.invalid/feed.xml",
                    type="rss",
                    priority=1,
                    category="official",
                )

                def collect_source(source_item, run_id):
                    return collect_rss(
                        source_item,
                        run_id,
                        client=client,
                        now=FIXED_NOW,
                    )

                async def sieve(run_id):
                    async def response(prompt):
                        return json.dumps(
                            [
                                {
                                    "url_hash": item["url_hash"],
                                    "decision": "KEEP",
                                    "reason": "Fixture contains a material AI update.",
                                    "confidence": 0.9,
                                    "scores": {"agent_relevance": 0.9},
                                }
                                for item in _candidate_list(prompt)
                            ]
                        )

                    return await run_sieve(run_id, request_fn=response)

                async def scout(run_id):
                    async def response(prompt):
                        return json.dumps(
                            [
                                {
                                    "url_hash": item["url_hash"],
                                    "title": item["title"],
                                    "what_happened": "The fixture records a documented AI update.",
                                    "why_it_matters": "It demonstrates the complete agent data path.",
                                    "plain_english_explanation": "The pipeline turns a feed item into a ranked signal.",
                                    "x_discussion_angle": "Discuss the verified automation boundary.",
                                    "score_breakdown": {
                                        "capability_shift": 80,
                                        "real_world_impact": 75,
                                        "agent_relevance": 90,
                                        "x_discussion_potential": 70,
                                        "novelty": 65,
                                        "source_quality": 85,
                                    },
                                }
                                for item in _candidate_list(prompt)
                            ]
                        )

                    return await run_scout(run_id, request_fn=response)

                def report_signals(run_id, limit):
                    return [
                        json.loads(row[5])
                        for row in get_top_scored_signals(run_id, limit)
                    ]

                def record_delivery(report):
                    deliveries.append(report)
                    return True

                dependencies = PipelineDependencies(
                    load_sources=lambda: [source],
                    collect_source=collect_source,
                    run_sieve=sieve,
                    run_scout=scout,
                    get_report_signals=report_signals,
                    send_telegram=record_delivery,
                    initialize_storage=init_db,
                    get_storage_counts=get_storage_counts,
                )
                summary = await run_pipeline(
                    deliver_report=False,
                    summary_path=Path(directory, "run_summary.json"),
                    dependencies=dependencies,
                )

            assert summary.status == "succeeded"
            assert summary.report_language == "English"
            assert 1 <= summary.report_signal_count <= 5
            assert not summary.delivery_attempted
            assert not deliveries
            print(
                "PASS — "
                f"{summary.report_signal_count} English signal(s), "
                f"{summary.sieve_evaluated} sieved, {summary.scout_analyzed} analyzed"
            )
        finally:
            if previous_db_path is None:
                os.environ.pop("SIGNALS_DB_PATH", None)
            else:
                os.environ["SIGNALS_DB_PATH"] = previous_db_path

    print("PASS — No external Gemini or Telegram service was contacted")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        asyncio.run(_run_validation())
    except Exception as exc:  # noqa: BLE001 - executable validation boundary
        print(
            f"FAIL — offline validation stopped: {type(exc).__name__}", file=sys.stderr
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
