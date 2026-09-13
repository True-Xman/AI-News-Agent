import os
import subprocess
import sys
import unittest


class ValidationScriptTests(unittest.TestCase):
    def test_offline_validation_identifies_itself_as_simulated(self):
        environment = os.environ.copy()
        for name in (
            "GOOGLE_API_KEY",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHANNEL_ID",
        ):
            environment.pop(name, None)

        result = subprocess.run(
            [sys.executable, "scripts/validate_offline.py"],
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("OFFLINE INTEGRATION VALIDATION"))
        self.assertIn(
            "No external Gemini or Telegram service was contacted",
            result.stdout,
        )

    def test_source_check_help_requires_no_credentials(self):
        result = subprocess.run(
            [sys.executable, "scripts/check_sources.py", "--help"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("live RSS source health", result.stdout)


if __name__ == "__main__":
    unittest.main()
