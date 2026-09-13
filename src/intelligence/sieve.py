"""Validated first-stage relevance filtering for fresh AI signals."""

import json
from collections.abc import Awaitable, Callable
from pathlib import Path

from ..errors import ResponseValidationError
from ..storage.operations import get_unprocessed_raw_signals, update_signal_filter
from .contracts import SieveResult, parse_json_value, validate_sieve_decisions
from .gemini_client import send_gemini_request

SIEVE_INPUT_LIMIT = 50
SIEVE_BATCH_SIZE = 5
PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "sieve_prompt.md"
SIEVE_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")


async def run_sieve(
    run_id: str,
    request_fn: Callable[[str], Awaitable[str]] | None = None,
) -> SieveResult:
    """Classify every selected row or fail without partially applying a batch."""
    rows = get_unprocessed_raw_signals(run_id=run_id, limit=SIEVE_INPUT_LIMIT)
    if not rows:
        return SieveResult(evaluated=0, kept=0, discarded=0)

    request = request_fn or send_gemini_request
    kept = discarded = 0

    for offset in range(0, len(rows), SIEVE_BATCH_SIZE):
        batch = rows[offset : offset + SIEVE_BATCH_SIZE]
        candidates = [
            {
                "url_hash": row[0],
                "title": row[1],
                "source": row[2],
                "snippet": row[5] or "",
            }
            for row in batch
        ]
        prompt = (
            f"{SIEVE_PROMPT_TEMPLATE}\n\n"
            "Candidates:\n"
            f"{json.dumps(candidates, ensure_ascii=False)}"
        )

        raw_value = parse_json_value(await request(prompt), list)
        decisions = validate_sieve_decisions(raw_value)
        response_hashes = [decision.url_hash for decision in decisions]
        expected_hashes = {candidate["url_hash"] for candidate in candidates}

        if len(response_hashes) != len(set(response_hashes)):
            raise ResponseValidationError(
                "Sieve response contains duplicate URL hashes"
            )
        if set(response_hashes) != expected_hashes:
            raise ResponseValidationError(
                "Sieve response hashes do not exactly match the submitted batch"
            )

        for decision in decisions:
            update_signal_filter(
                decision.url_hash,
                decision.decision,
                decision.reason,
                decision.confidence,
                decision.scores,
                run_id=run_id,
            )
            if decision.decision == "KEEP":
                kept += 1
            else:
                discarded += 1

    return SieveResult(evaluated=len(rows), kept=kept, discarded=discarded)
