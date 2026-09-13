import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.collectors.rss_collector import SourceCollectionResult
from src.config.config_loader import SourceItem
from src.errors import ConfigurationError, ExternalServiceError, ResponseValidationError
from src.intelligence.contracts import ScoutResult, SieveResult
from src.pipeline import PipelineDependencies, run_pipeline
from src.reporting.telegram import TelegramClient


VALID_SIGNAL = {
    "title": "Verified signal",
    "score": 80.0,
    "what_happened": "A documented capability changed.",
    "why_it_matters": "The change affects agent workflows.",
    "plain_english_explanation": "The tool can now complete a useful task.",
    "x_discussion_angle": "Discuss the measured workflow impact.",
    "source_url": "https://example.com/signal",
}


def make_dependencies(
    report_signals=None,
    telegram_result=True,
    source_results=None,
    sieve_error=None,
    observed_run_ids=None,
):
    sources = [
        SourceItem(
            name=f"Fixture {index}",
            url=f"https://feed-{index}.test/rss",
            type="rss",
            priority=index + 1,
            category="official",
        )
        for index in range(len(source_results or [True]))
    ]

    async def sieve(run_id):
        if sieve_error:
            raise sieve_error
        return SieveResult(evaluated=0, kept=0, discarded=0)

    async def scout(run_id):
        return ScoutResult(analyzed=0, selected=len(report_signals or []))

    def collect_source(source, run_id):
        index = source.priority - 1
        healthy = (source_results or [True])[index]
        return SourceCollectionResult(
            source_name=source.name,
            healthy=healthy,
            entries_parsed=1,
            recent_entries=1,
            inserted=1 if healthy else 0,
            error_category=None if healthy else "http_503",
        )

    def get_report_signals(run_id, limit):
        if observed_run_ids is not None:
            observed_run_ids.append(run_id)
        return list(report_signals or [])[:limit]

    return PipelineDependencies(
        load_sources=lambda: sources,
        collect_source=collect_source,
        run_sieve=sieve,
        run_scout=scout,
        get_report_signals=get_report_signals,
        send_telegram=lambda report: telegram_result,
    )


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_new_signals_succeeds_without_delivery(self):
        summary = await run_pipeline(
            deliver_report=True,
            dependencies=make_dependencies(),
        )

        self.assertEqual(summary.status, "no_new_report")
        self.assertFalse(summary.delivery_attempted)

    async def test_requested_delivery_failure_raises_and_writes_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "summary.json")
            with self.assertRaises(ExternalServiceError):
                await run_pipeline(
                    deliver_report=True,
                    summary_path=path,
                    dependencies=make_dependencies([VALID_SIGNAL], telegram_result=False),
                )

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "failed")
            self.assertEqual(payload["failure_category"], "ExternalServiceError")
            self.assertTrue(payload["delivery_attempted"])

    async def test_source_health_below_sixty_percent_fails(self):
        with self.assertRaises(ExternalServiceError):
            await run_pipeline(
                deliver_report=False,
                dependencies=make_dependencies(source_results=[True, True, False, False]),
            )

    async def test_model_validation_error_propagates(self):
        error = ResponseValidationError("malformed model response")
        with self.assertRaises(ResponseValidationError):
            await run_pipeline(
                deliver_report=False,
                dependencies=make_dependencies(sieve_error=error),
            )

    async def test_report_query_uses_the_active_run_id(self):
        observed = []

        summary = await run_pipeline(
            deliver_report=False,
            dependencies=make_dependencies([VALID_SIGNAL], observed_run_ids=observed),
        )

        self.assertEqual(observed, [summary.run_id])
        self.assertEqual(summary.report_signal_count, 1)

    async def test_state_restored_is_parsed_strictly(self):
        with patch.dict(os.environ, {"STATE_RESTORED": "TrUe"}):
            summary = await run_pipeline(
                deliver_report=False,
                dependencies=make_dependencies(),
            )
        self.assertTrue(summary.state_restored)


class ImportAndConfigurationTests(unittest.TestCase):
    def test_main_imports_without_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            import src.main

    def test_telegram_configuration_error_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                TelegramClient()


if __name__ == "__main__":
    unittest.main()
