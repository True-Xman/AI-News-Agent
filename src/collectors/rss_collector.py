"""HTTP-explicit RSS collection with deterministic freshness accounting."""

import calendar
import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import feedparser
import httpx

from ..models.raw_signal import RawSignal
from ..storage.operations import insert_raw_signal

MAX_ITEM_AGE_DAYS = 7
MAX_FUTURE_SKEW_HOURS = 24
MAX_SNIPPET_CHARS = 1500
REQUEST_TIMEOUT_SECONDS = 20.0
USER_AGENT = "AI-Signal-Scout/1.0 (+https://github.com/True-Xman/AI-News-Agent)"

logger = logging.getLogger(__name__)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class SourceCollectionResult:
    source_name: str
    healthy: bool
    entries_parsed: int = 0
    recent_entries: int = 0
    inserted: int = 0
    duplicates: int = 0
    undated: int = 0
    error_category: str | None = None


def _clean_snippet(value) -> str:
    text = html.unescape(HTML_TAG_PATTERN.sub(" ", str(value or "")))
    return " ".join(text.split())[:MAX_SNIPPET_CHARS]


def _entry_timestamp(entry) -> float | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed is None:
        return None
    return float(calendar.timegm(parsed))


def collect_rss(
    source_item,
    run_id: str,
    client: httpx.Client | None = None,
    now: datetime | None = None,
) -> SourceCollectionResult:
    """Fetch one feed and store only current, linked entries."""
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    current_time = current_time.astimezone(timezone.utc)

    owns_client = client is None
    request_client = client or httpx.Client(
        follow_redirects=True,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
    )

    try:
        response = request_client.get(
            source_item.url,
            follow_redirects=True,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        category = f"http_{exc.response.status_code}"
        logger.warning("Source %s failed: %s", source_item.name, category)
        return SourceCollectionResult(source_item.name, False, error_category=category)
    except httpx.RequestError:
        logger.warning("Source %s failed: request_error", source_item.name)
        return SourceCollectionResult(
            source_item.name,
            False,
            error_category="request_error",
        )
    finally:
        if owns_client:
            request_client.close()

    try:
        feed = feedparser.parse(response.content)
    except Exception:  # noqa: BLE001 - feedparser exposes no stable exception hierarchy
        logger.warning("Source %s failed: parse_error", source_item.name)
        return SourceCollectionResult(
            source_item.name, False, error_category="parse_error"
        )

    entries = list(feed.entries)
    if feed.bozo and not entries:
        logger.warning("Source %s failed: parse_error", source_item.name)
        return SourceCollectionResult(
            source_item.name, False, error_category="parse_error"
        )

    oldest_allowed = current_time - timedelta(days=MAX_ITEM_AGE_DAYS)
    newest_allowed = current_time + timedelta(hours=MAX_FUTURE_SKEW_HOURS)
    recent_entries = inserted = duplicates = undated = 0

    for entry in entries:
        link = str(entry.get("link") or "").strip()
        if not link:
            continue

        timestamp = _entry_timestamp(entry)
        if timestamp is None:
            undated += 1
            found_at = current_time.timestamp()
        else:
            published_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            if published_at < oldest_allowed or published_at > newest_allowed:
                continue
            found_at = timestamp

        recent_entries += 1
        signal = RawSignal(
            url=link,
            title=str(entry.get("title") or "Untitled signal").strip(),
            source=source_item.name,
            source_id=source_item.priority,
            found_at=found_at,
            snippet=_clean_snippet(entry.get("summary") or entry.get("description")),
            category=source_item.category,
        )
        if insert_raw_signal(signal, run_id):
            inserted += 1
        else:
            duplicates += 1

    logger.info(
        "Source %s healthy: parsed=%s recent=%s inserted=%s duplicates=%s",
        source_item.name,
        len(entries),
        recent_entries,
        inserted,
        duplicates,
    )
    return SourceCollectionResult(
        source_name=source_item.name,
        healthy=True,
        entries_parsed=len(entries),
        recent_entries=recent_entries,
        inserted=inserted,
        duplicates=duplicates,
        undated=undated,
    )
