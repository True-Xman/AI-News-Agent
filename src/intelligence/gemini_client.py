import asyncio
import logging
import os
from collections.abc import Callable
from typing import Any

from google import genai
from google.genai.errors import APIError

from ..errors import ConfigurationError, ExternalServiceError, ResponseValidationError


logger = logging.getLogger(__name__)


def create_gemini_client(api_key: str | None = None) -> genai.Client:
    """Create a Gemini client only when a live request is about to run."""
    resolved_key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not resolved_key:
        raise ConfigurationError("GOOGLE_API_KEY is required for live Gemini requests")
    return genai.Client(api_key=resolved_key)


async def send_gemini_request(
    prompt: str,
    max_retries: int = 3,
    client_factory: Callable[[], Any] | None = None,
) -> str:
    """Send prompt to Gemini with exponential backoff for 429/503 errors."""
    if max_retries < 1:
        raise ValueError("max_retries must be at least 1")

    client = (client_factory or create_gemini_client)()

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )
            if not isinstance(response.text, str) or not response.text.strip():
                raise ResponseValidationError("Gemini returned an empty response")
            return response.text
        except APIError as e:
            code = getattr(e, "code", None)
            message = str(e).lower()
            quota_exhausted = code == 429 and any(
                marker in message for marker in ("daily", "quota", "exceeded")
            )
            retryable = code in {429, 503} and not quota_exhausted

            if retryable and attempt < max_retries - 1:
                wait = 2**attempt
                logger.warning(
                    "Temporary Gemini error (status %s); retrying in %s second(s)",
                    code,
                    wait,
                )
                await asyncio.sleep(wait)
                continue

            raise ExternalServiceError(
                f"Gemini request failed with status {code or 'unknown'}"
            ) from e

    raise ExternalServiceError("Gemini request exhausted all retries")

