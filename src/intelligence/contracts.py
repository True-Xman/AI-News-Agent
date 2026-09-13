"""Strict response contracts for model-assisted pipeline stages."""

import json
import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from typing import Literal

from ..errors import ResponseValidationError


FENCED_JSON_PATTERN = re.compile(
    r"^\s*```(?:json)?\s*(.*?)\s*```\s*$",
    flags=re.IGNORECASE | re.DOTALL,
)


def parse_json_value(text: str, expected_type: type[list] | type[dict]):
    """Extract one JSON list or object from a possibly fenced response."""
    if not isinstance(text, str) or not text.strip():
        raise ResponseValidationError("Model response did not contain JSON")

    candidate = text.strip()
    fence_match = FENCED_JSON_PATTERN.match(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()

    opening = "[" if expected_type is list else "{"
    start = candidate.find(opening)
    if start < 0:
        raise ResponseValidationError(
            f"Model response did not contain a JSON {expected_type.__name__}"
        )

    try:
        value, _ = json.JSONDecoder().raw_decode(candidate[start:])
    except json.JSONDecodeError as exc:
        raise ResponseValidationError("Model response contained invalid JSON") from exc

    if not isinstance(value, expected_type):
        raise ResponseValidationError(
            f"Model response must be a JSON {expected_type.__name__}"
        )
    return value


class SieveDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url_hash: str = Field(min_length=1)
    decision: Literal["KEEP", "DISCARD"]
    reason: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    scores: dict[str, float]

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason must not be blank")
        return value.strip()

    @field_validator("scores")
    @classmethod
    def scores_must_be_in_range(cls, value: dict[str, float]) -> dict[str, float]:
        if any(score < 0 or score > 1 for score in value.values()):
            raise ValueError("Sieve scores must be between 0 and 1")
        return value


def validate_sieve_decisions(value: list) -> list[SieveDecision]:
    try:
        return [SieveDecision.model_validate(item) for item in value]
    except (ValidationError, TypeError) as exc:
        raise ResponseValidationError("Sieve response violated its JSON contract") from exc


@dataclass(frozen=True)
class SieveResult:
    evaluated: int
    kept: int
    discarded: int
