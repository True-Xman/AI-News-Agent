from datetime import datetime, timezone
from pathlib import Path

import httpx

from src.collectors.rss_collector import collect_rss
from src.config.config_loader import SourceItem
from tests.helpers import TemporaryDatabaseTestCase


FIXTURE_BYTES = Path("tests/fixtures/sample_feed.xml").read_bytes()


class RssCollectorTests(TemporaryDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        self.source = SourceItem(
            name="Fixture",
            url="https://feed.test/rss",
            type="rss",
            priority=1,
            category="official",
        )

    def test_collection_counts_insert_duplicate_old_and_future_entries(self):
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=FIXTURE_BYTES)
        )
        with httpx.Client(transport=transport) as client:
            first = collect_rss(self.source, "run-1", client=client, now=self.now)
            second = collect_rss(self.source, "run-2", client=client, now=self.now)

        self.assertTrue(first.healthy)
        self.assertEqual(
            (first.entries_parsed, first.recent_entries, first.inserted),
            (4, 2, 2),
        )
        self.assertEqual(first.undated, 1)
        self.assertEqual(second.duplicates, 2)

    def test_non_2xx_response_is_an_unhealthy_source(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(404))
        with httpx.Client(transport=transport) as client:
            result = collect_rss(self.source, "run-1", client=client, now=self.now)

        self.assertFalse(result.healthy)
        self.assertEqual(result.error_category, "http_404")
