"""
Tests for the Persian report formatter.
"""

import sys
import os
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reporting.formatter import format_persian_report, escape_markdown_v2


class TestPersianReportFormatter(unittest.TestCase):

    def test_formatter_output_starts_with_header(self):
        """Test that the formatted report starts with the correct header."""
        signals = [
            {
                "title": "Test Signal",
                "score": 85.0,
                "what_happened": "Test what happened",
                "why_it_matters": "Test why matters",
                "eli5": "Test explanation",
                "x_angle": "Test x angle",
                "source_url": "https://example.com"
            }
        ]
        result = format_persian_report(signals)
        self.assertTrue(result.startswith("🤖 AI Signal Scout\nگزارش هوش مصنوعی روزانه\n"))

    def test_formatter_empty_signals(self):
        """Test that formatting empty signals returns a no-signal message."""
        result = format_persian_report([])
        self.assertIn("هیچ سیگنالی برای گزارش یافت نشد", result)

    def test_formatter_missing_fields(self):
        """Test that missing fields are handled gracefully."""
        # Signal with some missing fields
        signals = [
            {
                "title": "Incomplete Signal",
                "score": None,  # Missing score
                # Missing what_happened
                "why_it_matters": "Important update",
                "eli5": "Simple explanation",
                "x_angle": "Discussion potential high",
                "source_url": ""
            }
        ]
        result = format_persian_report(signals)
        # Should not crash and should contain the title
        self.assertIn("Incomplete Signal", result)

    def test_formatter_limits_what_happened_to_3_lines(self):
        """Test that what_happened is limited to 3 lines."""
        signals = [
            {
                "title": "Test",
                "score": 50.0,
                "what_happened": "Line 1\nLine 2\nLine 3\nLine 4\nLine 5",
                "why_it_matters": "Reason",
                "eli5": "Explanation",
                "x_angle": "X angle",
                "source_url": "http://test.com"
            }
        ]
        result = format_persian_report(signals)
        # Should contain Line 1, Line 2, Line 3 but NOT Line 4 or Line 5
        self.assertIn("Line 1", result)
        self.assertIn("Line 2", result)
        self.assertIn("Line 3", result)
        # Verify truncation happened by checking that Line 4 is NOT in the result
        self.assertNotIn("Line 4", result)
        self.assertNotIn("Line 5", result)

    def test_markdown_escaping(self):
        """Test that special markdown characters are escaped."""
        text = "Test with *asterisk* and _underscore_"
        escaped = escape_markdown_v2(text)
        self.assertIn(r'\*', escaped)
        self.assertIn(r'\_', escaped)


if __name__ == "__main__":
    unittest.main()