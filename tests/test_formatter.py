import unittest
from datetime import datetime, timezone

from src.errors import ResponseValidationError
from src.reporting.formatter import format_report, strip_telegram_html, validate_report


SAMPLE_SIGNAL = {
    "title": "Verified capability update",
    "score": 84.5,
    "what_happened": "The source announced a measured capability change.",
    "why_it_matters": "The change affects practical agent workflows.",
    "plain_english_explanation": "The tool can now complete a useful task more reliably.",
    "x_discussion_angle": "Discuss the measured impact and remaining limits.",
    "source_url": "https://example.com/verified-update",
}


class EnglishReportFormatterTests(unittest.TestCase):
    def test_report_uses_compact_english_screenshot_layout(self):
        report = format_report(
            [SAMPLE_SIGNAL],
            generated_at=datetime(2026, 9, 13, tzinfo=timezone.utc),
        )

        self.assertEqual(
            strip_telegram_html(report).splitlines(),
            [
                "AI SIGNAL SCOUT",
                "AUTONOMOUS AI INTELLIGENCE BRIEF",
                "2026-09-13 UTC · TOP 1",
                "1 · 84.5/100 · Verified capability update",
                "Why: The change affects practical agent workflows. · Source ↗",
                "Live RSS → Gemini analysis → deterministic ranking → Telegram",
            ],
        )
        self.assertIn("<b>AI SIGNAL SCOUT</b>", report)
        self.assertIn(
            "<b>1 · 84.5/100 · Verified capability update</b>",
            report,
        )
        self.assertIn(
            '<a href="https://example.com/verified-update">Source ↗</a>',
            report,
        )

    def test_report_stays_within_one_frame_budget(self):
        signals = [
            {
                **SAMPLE_SIGNAL,
                "title": "Long title " * 30,
                "why_it_matters": "Long reason " * 40,
                "source_url": f"https://example.com/{index}",
            }
            for index in range(5)
        ]

        report = format_report(signals)
        visible = strip_telegram_html(report)

        self.assertLessEqual(len(visible), 1_000)
        self.assertLessEqual(len(visible.splitlines()), 15)

    def test_report_rejects_arabic_script(self):
        with self.assertRaisesRegex(ResponseValidationError, "Arabic-script"):
            validate_report("گزارش", item_count=1)

    def test_report_escapes_dynamic_html(self):
        signal = {**SAMPLE_SIGNAL, "title": "R&D <verified>"}

        report = format_report([signal])

        self.assertIn("R&amp;D &lt;verified&gt;", report)

    def test_report_rejects_non_https_source(self):
        signal = {**SAMPLE_SIGNAL, "source_url": "http://example.com/item"}

        with self.assertRaisesRegex(ResponseValidationError, "HTTPS"):
            format_report([signal])


if __name__ == "__main__":
    unittest.main()
