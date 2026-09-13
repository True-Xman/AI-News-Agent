"""Structured analysis, deterministic scoring, and diverse Top-5 selection."""

import json
from collections import Counter
from collections.abc import Awaitable, Callable
from pathlib import Path

from ..errors import ResponseValidationError
from ..storage.operations import get_keep_signals, insert_processed_signal
from ..utils.organization import get_organization
from .contracts import (
    ScoreBreakdown,
    ScoutResult,
    parse_json_value,
    validate_scout_analyses,
)
from .gemini_client import send_gemini_request


SCOUT_INPUT_LIMIT = 15
REPORT_LIMIT = 5
MAX_PER_SOURCE_FIRST_PASS = 2
PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "scout_prompt.md"
SCOUT_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")


def calculate_weighted_score(scores: ScoreBreakdown) -> float:
    """Calculate the documented score without trusting a model-generated total."""
    return round(
        scores.capability_shift * 0.25
        + scores.real_world_impact * 0.20
        + scores.agent_relevance * 0.20
        + scores.x_discussion_potential * 0.15
        + scores.novelty * 0.10
        + scores.source_quality * 0.10,
        1,
    )


def select_diverse(
    signals: list[dict],
    limit: int = REPORT_LIMIT,
    max_per_source: int = MAX_PER_SOURCE_FIRST_PASS,
) -> list[dict]:
    """Rank deterministically, then favor source diversity before filling slots."""
    ranked = sorted(
        signals,
        key=lambda signal: (
            -float(signal.get("score", 0)),
            -float(signal.get("found_at", 0)),
            str(signal.get("url_hash", "")),
        ),
    )
    selected: list[dict] = []
    leftovers: list[dict] = []
    source_counts: Counter[str] = Counter()

    for signal in ranked:
        organization = str(signal.get("organization") or "Unknown")
        if source_counts[organization] < max_per_source and len(selected) < limit:
            selected.append(signal)
            source_counts[organization] += 1
        else:
            leftovers.append(signal)

    if len(selected) < limit:
        selected.extend(leftovers[: limit - len(selected)])
    return selected


async def run_scout(
    run_id: str,
    request_fn: Callable[[str], Awaitable[str]] | None = None,
) -> ScoutResult:
    """Analyze every supplied KEEP row and persist only the deterministic Top 5."""
    rows = get_keep_signals(run_id=run_id, limit=SCOUT_INPUT_LIMIT)
    if not rows:
        return ScoutResult(analyzed=0, selected=0)

    originals = {
        row[0]: {
            "title": row[1],
            "source": row[2],
            "found_at": row[4],
            "source_url": row[11],
        }
        for row in rows
    }
    candidates = [
        {
            "url_hash": row[0],
            "title": row[1],
            "source": row[2],
            "snippet": row[5] or "",
        }
        for row in rows
    ]
    prompt = (
        f"{SCOUT_PROMPT_TEMPLATE}\n\n"
        "Candidates:\n"
        f"{json.dumps(candidates, ensure_ascii=False)}"
    )

    request = request_fn or send_gemini_request
    raw_value = parse_json_value(await request(prompt), list)
    analyses = validate_scout_analyses(raw_value)
    response_hashes = [analysis.url_hash for analysis in analyses]
    expected_hashes = set(originals)

    if len(response_hashes) != len(set(response_hashes)):
        raise ResponseValidationError("Scout response contains duplicate URL hashes")
    if set(response_hashes) != expected_hashes:
        raise ResponseValidationError(
            "Scout response hashes do not exactly match the submitted candidates"
        )

    scored: list[dict] = []
    for analysis in analyses:
        original = originals[analysis.url_hash]
        payload = analysis.model_dump(exclude={"source_url"})
        payload.update(
            {
                "title": original["title"],
                "source_url": original["source_url"],
                "organization": get_organization(
                    original["source_url"], original["source"] or "Unknown"
                ),
                "found_at": original["found_at"],
                "score": calculate_weighted_score(analysis.score_breakdown),
            }
        )
        scored.append(payload)

    selected = select_diverse(scored)
    for signal in selected:
        insert_processed_signal(
            title=signal["title"],
            url=signal["source_url"],
            score=signal["score"],
            topic_fingerprint=signal["title"].strip().casefold(),
            analysis_json=signal,
            run_id=run_id,
        )

    return ScoutResult(analyzed=len(rows), selected=len(selected))
