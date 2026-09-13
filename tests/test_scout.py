import asyncio
import hashlib
import json
import unittest

from src.errors import ResponseValidationError
from src.intelligence.contracts import ScoreBreakdown
from src.intelligence.scout import (
    calculate_weighted_score,
    run_scout,
    select_diverse,
)
from src.storage.operations import (
    get_top_scored_signals,
    insert_raw_signal,
    update_signal_filter,
)
from tests.helpers import TemporaryDatabaseTestCase, make_raw_signal


class ScoutSelectionTests(unittest.TestCase):
    def test_weighted_score_is_computed_in_python(self):
        breakdown = ScoreBreakdown(
            capability_shift=100,
            real_world_impact=80,
            agent_relevance=60,
            x_discussion_potential=40,
            novelty=20,
            source_quality=100,
        )

        self.assertEqual(calculate_weighted_score(breakdown), 71.0)

    def test_two_pass_diversity_fills_five_slots(self):
        signals = [
            {
                "title": f"Signal {index}",
                "organization": organization,
                "score": 100 - index,
                "found_at": 100 - index,
                "url_hash": str(index),
            }
            for index, organization in enumerate(
                ("OpenAI", "OpenAI", "OpenAI", "DeepMind", "OWASP", "arXiv")
            )
        ]

        selected = select_diverse(signals, limit=5, max_per_source=2)

        self.assertEqual(len(selected), 5)
        self.assertLessEqual(
            sum(signal["organization"] == "OpenAI" for signal in selected[:4]),
            2,
        )

    def test_ties_are_sorted_by_recency_then_hash(self):
        signals = [
            {"organization": "A", "score": 80, "found_at": 10, "url_hash": "b"},
            {"organization": "B", "score": 80, "found_at": 20, "url_hash": "c"},
            {"organization": "C", "score": 80, "found_at": 20, "url_hash": "a"},
        ]

        selected = select_diverse(signals, limit=3)

        self.assertEqual([signal["url_hash"] for signal in selected], ["a", "c", "b"])


class ScoutPipelineTests(TemporaryDatabaseTestCase):
    def _insert_keep_signals(self, count):
        hashes = []
        urls = []
        for index in range(count):
            url = f"https://source-{index}.example/item"
            signal = make_raw_signal(
                url,
                source=f"Organization {index}",
                source_id=index + 1,
                found_at=1000 - index,
            )
            insert_raw_signal(signal, "run-1")
            url_hash = hashlib.md5(url.encode()).hexdigest()
            update_signal_filter(
                url_hash,
                "KEEP",
                "Relevant",
                confidence=0.9,
                scores={},
                run_id="run-1",
            )
            hashes.append(url_hash)
            urls.append(url)
        return hashes, urls

    @staticmethod
    def _analysis(url_hash, index=0):
        score = 100 - index
        return {
            "url_hash": url_hash,
            "title": f"Model title {index}",
            "what_happened": "A measured capability changed.",
            "why_it_matters": "The change affects agent workflows.",
            "plain_english_explanation": "The system can complete a useful task.",
            "x_discussion_angle": "Discuss measured impact and limits.",
            "source_url": "https://model.invalid/hallucinated",
            "score_breakdown": {
                "capability_shift": score,
                "real_world_impact": score,
                "agent_relevance": score,
                "x_discussion_potential": score,
                "novelty": score,
                "source_quality": score,
            },
        }

    def test_requires_every_supplied_hash(self):
        hashes, _ = self._insert_keep_signals(2)

        async def incomplete_response(prompt):
            return json.dumps([self._analysis(hashes[0])])

        with self.assertRaises(ResponseValidationError):
            asyncio.run(run_scout("run-1", request_fn=incomplete_response))

    def test_restores_source_urls_and_inserts_only_five(self):
        hashes, urls = self._insert_keep_signals(6)

        async def complete_response(prompt):
            return json.dumps(
                [self._analysis(url_hash, index) for index, url_hash in enumerate(hashes)]
            )

        result = asyncio.run(run_scout("run-1", request_fn=complete_response))
        rows = get_top_scored_signals("run-1", limit=10)

        self.assertEqual((result.analyzed, result.selected), (6, 5))
        self.assertEqual(len(rows), 5)
        self.assertEqual([row[2] for row in rows], urls[:5])
        self.assertNotIn("model.invalid", json.dumps([json.loads(row[5]) for row in rows]))


if __name__ == "__main__":
    unittest.main()
