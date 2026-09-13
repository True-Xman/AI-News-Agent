import asyncio
import hashlib
import json

from src.errors import ResponseValidationError
from src.intelligence.contracts import parse_json_value
from src.intelligence.sieve import run_sieve
from src.storage.operations import get_keep_signals, insert_raw_signal
from tests.helpers import TemporaryDatabaseTestCase, make_raw_signal


class SieveTests(TemporaryDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.hashes = []
        for index in range(2):
            signal = make_raw_signal(
                f"https://example.com/{index}",
                source=f"Source {index}",
                source_id=index + 1,
            )
            insert_raw_signal(signal, "run-1")
            self.hashes.append(hashlib.md5(signal.url.encode()).hexdigest())

    def test_rejects_missing_and_unknown_hashes(self):
        async def incomplete_response(prompt):
            return (
                '[{"url_hash":"unknown","decision":"KEEP","reason":"x",'
                '"confidence":0.8,"scores":{}}]'
            )

        with self.assertRaises(ResponseValidationError):
            asyncio.run(run_sieve("run-1", request_fn=incomplete_response))

    def test_updates_every_row_from_a_complete_batch(self):
        async def complete_response(prompt):
            return json.dumps(
                [
                    {
                        "url_hash": self.hashes[0],
                        "decision": "KEEP",
                        "reason": "Material capability change",
                        "confidence": 0.9,
                        "scores": {"agent_relevance": 0.8},
                    },
                    {
                        "url_hash": self.hashes[1],
                        "decision": "DISCARD",
                        "reason": "Minor update",
                        "confidence": 0.8,
                        "scores": {"agent_relevance": 0.2},
                    },
                ]
            )

        result = asyncio.run(run_sieve("run-1", request_fn=complete_response))

        self.assertEqual((result.evaluated, result.kept, result.discarded), (2, 1, 1))
        self.assertEqual([row[0] for row in get_keep_signals("run-1")], [self.hashes[0]])

    def test_rejects_duplicate_response_hashes(self):
        async def duplicate_response(prompt):
            item = {
                "url_hash": self.hashes[0],
                "decision": "KEEP",
                "reason": "Material change",
                "confidence": 0.8,
                "scores": {},
            }
            return json.dumps([item, item])

        with self.assertRaisesRegex(ResponseValidationError, "duplicate"):
            asyncio.run(run_sieve("run-1", request_fn=duplicate_response))

    def test_rejects_invalid_decision_and_confidence(self):
        invalid_values = [
            {"decision": "MAYBE", "confidence": 0.8},
            {"decision": "KEEP", "confidence": 1.1},
        ]
        for invalid in invalid_values:
            with self.subTest(invalid=invalid):
                async def invalid_response(prompt, value=invalid):
                    return json.dumps(
                        [
                            {
                                "url_hash": self.hashes[index],
                                "reason": "Invalid contract value",
                                "scores": {},
                                **value,
                            }
                            for index in range(2)
                        ]
                    )

                with self.assertRaises(ResponseValidationError):
                    asyncio.run(run_sieve("run-1", request_fn=invalid_response))


class JsonExtractionTests(TemporaryDatabaseTestCase):
    def test_extracts_fenced_json(self):
        value = parse_json_value('```json\n[{"decision":"KEEP"}]\n```', list)
        self.assertEqual(value, [{"decision": "KEEP"}])
