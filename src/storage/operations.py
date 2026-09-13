import hashlib
import json
from collections import OrderedDict

from ..models.raw_signal import RawSignal
from ..utils.organization import get_organization
from .database import get_connection


def insert_raw_signal(signal: RawSignal, run_id: str) -> bool:
    """Insert a new URL once and report whether this call created the row."""
    conn = get_connection()
    cursor = conn.cursor()
    url_hash = hashlib.md5(signal.url.encode()).hexdigest()
    try:
        cursor.execute(
            """
            INSERT OR IGNORE INTO raw_signals
                (url_hash, title, source, source_id, found_at, snippet, url, run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                url_hash,
                signal.title,
                signal.source,
                signal.source_id,
                signal.found_at,
                signal.snippet,
                signal.url,
                run_id,
            ),
        )
        inserted = cursor.rowcount == 1
        conn.commit()
        return inserted
    finally:
        conn.close()


def _round_robin_by_source(rows: list[tuple], limit: int) -> list[tuple]:
    """Return one row per organization per pass, preserving stable row order."""
    if limit < 1:
        return []

    grouped: OrderedDict[str, list[tuple]] = OrderedDict()
    for row in rows:
        organization = get_organization(row[11], row[2] or "unknown")
        grouped.setdefault(organization, []).append(row)

    balanced: list[tuple] = []
    round_index = 0
    while len(balanced) < limit:
        added = False
        for source_rows in grouped.values():
            if round_index < len(source_rows):
                balanced.append(source_rows[round_index])
                added = True
                if len(balanced) == limit:
                    return balanced
        if not added:
            break
        round_index += 1
    return balanced


def get_unprocessed_raw_signals(run_id: str, limit: int = 50) -> list[tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT * FROM raw_signals
            WHERE filter_decision IS NULL AND run_id = ?
            ORDER BY source_id ASC, found_at DESC, url_hash ASC
            """,
            (run_id,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()
    return _round_robin_by_source(rows, limit)


def update_signal_filter(
    url_hash: str,
    decision: str,
    reason: str,
    confidence: float = 0.0,
    scores=None,
    run_id: str | None = None,
) -> None:
    if run_id is None:
        raise ValueError("run_id is required when updating a signal")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE raw_signals
            SET filter_decision = ?, filter_reason = ?, filter_confidence = ?,
                filter_scores = ?, filter_processed_at = datetime('now')
            WHERE url_hash = ? AND run_id = ?
            """,
            (
                decision,
                reason,
                confidence,
                json.dumps(scores) if scores else None,
                url_hash,
                run_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_keep_signals(run_id: str, limit: int = 15) -> list[tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT * FROM raw_signals
            WHERE filter_decision = 'KEEP' AND run_id = ?
            ORDER BY filter_confidence DESC, found_at DESC, source_id ASC, url_hash ASC
            """,
            (run_id,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()
    return _round_robin_by_source(rows, limit)


def insert_processed_signal(
    title: str,
    url: str,
    score: float,
    topic_fingerprint: str,
    analysis_json,
    run_id: str,
) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO processed_signals
                (title, url, score, topic_fingerprint, analysis_json, reported_at, run_id)
            VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
            """,
            (title, url, score, topic_fingerprint, json.dumps(analysis_json), run_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_top_scored_signals(run_id: str, limit: int = 5) -> list[tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT * FROM processed_signals
            WHERE run_id = ?
            ORDER BY score DESC, id ASC
            LIMIT ?
            """,
            (run_id, limit),
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_storage_counts() -> dict[str, int]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM raw_signals")
        raw_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM processed_signals")
        processed_count = cursor.fetchone()[0]
        return {"raw_signals": raw_count, "processed_signals": processed_count}
    finally:
        conn.close()
