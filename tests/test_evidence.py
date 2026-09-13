import json
import tempfile
import unittest
from pathlib import Path

from src.evidence import PipelineSummary, write_run_summary


class EvidenceTests(unittest.TestCase):
    def test_serialized_summary_contains_only_allowlisted_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "summary.json")
            summary = PipelineSummary(
                run_id="run-1",
                status="no_new_report",
                report_language="English",
            )

            write_run_summary(summary, path)
            payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(payload["report_language"], "English")
            forbidden = {
                "report_text",
                "channel_id",
                "message_id",
                "article_snippets",
                "local_path",
            }
            self.assertTrue(forbidden.isdisjoint(payload))


if __name__ == "__main__":
    unittest.main()
