import unittest
from pathlib import Path


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = Path(".github/workflows/daily_agent.yml").read_text(encoding="utf-8")

    def test_workflow_has_persistence_and_evidence_steps(self):
        for required in (
            "actions/cache/restore@v6",
            "actions/cache/save@v6",
            "data/signals.db",
            "actions/upload-artifact@v7",
            "artifacts/run_summary.json",
            "deliver_report:",
            "concurrency:",
            "python -m unittest discover -s tests -v",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.text)

    def test_tests_run_before_live_pipeline(self):
        self.assertLess(
            self.text.index("python -m unittest"),
            self.text.index("python -m src.main"),
        )

    def test_workflow_uses_current_actions_and_least_privilege(self):
        for required in (
            "permissions:\n  contents: read",
            "timeout-minutes: 15",
            "actions/checkout@v7",
            "actions/setup-python@v7",
            "if: success()",
            "STATE_RESTORED:",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.text)


if __name__ == "__main__":
    unittest.main()
