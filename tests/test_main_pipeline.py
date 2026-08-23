import unittest
import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestMainPipeline(unittest.TestCase):

    def test_main_imports(self):
        """Verify all main pipeline components import cleanly."""
        try:
            from src.config.config_loader import load_sources
            from src.collectors.rss_collector import collect_rss
            from src.storage.database import init_db
            from src.storage.operations import get_unprocessed_raw_signals, get_top_scored_signals
            from src.intelligence.sieve import run_sieve
            from src.intelligence.scout import run_scout
            from src.reporting.formatter import format_persian_report
            from src.reporting.telegram import TelegramClient
            import src.main
        except ImportError as e:
            self.fail(f"Pipeline import failed: {e}")

    def test_environment_variable_handling(self):
        """Verify TelegramClient raises clear error when environment variables are missing."""
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_CHANNEL_ID", None)
        
        from src.reporting.telegram import TelegramClient
        with self.assertRaises(ValueError):
            TelegramClient()

if __name__ == "__main__":
    unittest.main()
