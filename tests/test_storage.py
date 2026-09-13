from src.storage.operations import (
    get_top_scored_signals,
    get_unprocessed_raw_signals,
    insert_processed_signal,
    insert_raw_signal,
)
from tests.helpers import TemporaryDatabaseTestCase, make_raw_signal


class StorageTests(TemporaryDatabaseTestCase):
    def test_insert_reports_new_then_duplicate(self):
        signal = make_raw_signal("https://example.com/one", source="A")

        self.assertTrue(insert_raw_signal(signal, "run-1"))
        self.assertFalse(insert_raw_signal(signal, "run-2"))

    def test_top_scores_are_scoped_to_run(self):
        insert_processed_signal(
            "Old", "https://old", 99, "old", {"title": "Old"}, "old-run"
        )
        insert_processed_signal(
            "New", "https://new", 70, "new", {"title": "New"}, "new-run"
        )

        rows = get_top_scored_signals("new-run", limit=5)

        self.assertEqual([row[1] for row in rows], ["New"])

    def test_unprocessed_rows_are_round_robin_balanced_and_limited(self):
        signals = [
            make_raw_signal("https://a/new", source="A", source_id=1, found_at=200),
            make_raw_signal("https://a/old", source="A", source_id=1, found_at=100),
            make_raw_signal("https://b/one", source="B", source_id=2, found_at=150),
            make_raw_signal("https://c/one", source="C", source_id=3, found_at=120),
        ]
        for signal in signals:
            insert_raw_signal(signal, "run-1")

        rows = get_unprocessed_raw_signals("run-1", limit=3)

        self.assertEqual(len(rows), 3)
        self.assertEqual([row[2] for row in rows], ["A", "B", "C"])
        self.assertEqual(rows[0][11], "https://a/new")
