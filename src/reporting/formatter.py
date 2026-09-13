"""Compact, English-only Telegram report formatting."""

import html
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from ..errors import ResponseValidationError


REPORT_LIMIT = 5
MAX_TITLE_CHARS = 60
MAX_REASON_CHARS = 72
MAX_REPORT_VISIBLE_CHARS = 1_000
MAX_REPORT_LINES = 15
PROVENANCE_LINE = "Live RSS → Gemini analysis → deterministic ranking → Telegram"
ARABIC_SCRIPT_PATTERN = re.compile(r"[\u0600-\u06ff]")
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
SOURCE_LINK_PATTERN = re.compile(r'<a href="([^"]+)">Source ↗</a>')


def contains_arabic_script(text: str) -> bool:
    return bool(ARABIC_SCRIPT_PATTERN.search(text))


def strip_telegram_html(report: str) -> str:
    """Return the visible text represented by the formatter's small HTML subset."""
    return html.unescape(HTML_TAG_PATTERN.sub("", report))


def _ellipsize(value, limit: int, fallback: str) -> str:
    text = " ".join(str(value or fallback).split())
    if len(text) <= limit:
        return text
    prefix = text[: limit - 1].rstrip()
    if " " in prefix:
        prefix = prefix.rsplit(" ", 1)[0]
    return f"{prefix}…"


def _validate_https_url(value) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ResponseValidationError("Every report item requires an HTTPS source URL")
    return url


def validate_report(report: str, item_count: int) -> None:
    """Validate the one-frame English report boundary before delivery."""
    if contains_arabic_script(report):
        raise ResponseValidationError("Report contains Arabic-script characters")
    if not 1 <= item_count <= REPORT_LIMIT:
        raise ResponseValidationError("Report item count must be between 1 and 5")

    visible = strip_telegram_html(report)
    lines = visible.splitlines()
    if len(visible) > MAX_REPORT_VISIBLE_CHARS or len(lines) > MAX_REPORT_LINES:
        raise ResponseValidationError("Report exceeds the one-frame screenshot budget")
    if len(lines) != 4 + (2 * item_count):
        raise ResponseValidationError("Report does not match the compact item structure")
    if lines[:2] != ["AI SIGNAL SCOUT", "AUTONOMOUS AI INTELLIGENCE BRIEF"]:
        raise ResponseValidationError("Report header is invalid")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} UTC · TOP \d", lines[2]):
        raise ResponseValidationError("Report date and count header is invalid")
    if lines[2].rsplit(" ", 1)[-1] != str(item_count):
        raise ResponseValidationError("Report header count does not match report items")
    if lines[-1] != PROVENANCE_LINE:
        raise ResponseValidationError("Report provenance line is invalid")

    links = SOURCE_LINK_PATTERN.findall(report)
    if len(links) != item_count:
        raise ResponseValidationError("Report must contain one source link per item")
    for escaped_url in links:
        _validate_https_url(html.unescape(escaped_url))


def format_report(
    signals: list[dict],
    generated_at: datetime | None = None,
) -> str:
    """Format up to five current-run signals as one screenshot-ready card."""
    if not signals:
        return ""
    if len(signals) > REPORT_LIMIT:
        raise ResponseValidationError("Report item count must be between 1 and 5")

    timestamp = generated_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    date_text = timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d UTC")

    lines = [
        "<b>AI SIGNAL SCOUT</b>",
        "AUTONOMOUS AI INTELLIGENCE BRIEF",
        f"{date_text} · TOP {len(signals)}",
    ]
    for position, signal in enumerate(signals, 1):
        title = html.escape(
            _ellipsize(signal.get("title"), MAX_TITLE_CHARS, "Untitled signal"),
            quote=True,
        )
        reason = html.escape(
            _ellipsize(
                signal.get("why_it_matters"),
                MAX_REASON_CHARS,
                "Details were not provided.",
            ),
            quote=True,
        )
        try:
            score = float(signal.get("score", 0) or 0)
        except (TypeError, ValueError) as exc:
            raise ResponseValidationError("Report score must be numeric") from exc
        if not 0 <= score <= 100:
            raise ResponseValidationError("Report score must be between 0 and 100")
        source_url = html.escape(
            _validate_https_url(signal.get("source_url")),
            quote=True,
        )
        lines.extend(
            [
                f"<b>{position} · {score:.1f}/100 · {title}</b>",
                f'Why: {reason} · <a href="{source_url}">Source ↗</a>',
            ]
        )
    lines.append(PROVENANCE_LINE)

    report = "\n".join(lines)
    validate_report(report, item_count=len(signals))
    return report
