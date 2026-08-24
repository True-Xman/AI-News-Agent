import hashlib
import json
import logging
from .database import get_connection
from ..models.raw_signal import RawSignal
from ..utils.organization import get_organization

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def insert_raw_signal(signal: RawSignal, run_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    url_hash = hashlib.md5(signal.url.encode()).hexdigest()
    try:
        cursor.execute("""
        INSERT INTO raw_signals (url_hash, title, source, source_id, found_at, snippet, url, run_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url_hash) DO UPDATE SET 
            run_id = excluded.run_id,
            filter_decision = NULL,
            filter_reason = NULL,
            filter_confidence = NULL,
            filter_scores = NULL,
            filter_processed_at = NULL
        """, (url_hash, signal.title, signal.source, signal.source_id, signal.found_at, signal.snippet, signal.url, run_id))
        conn.commit()
    finally:
        conn.close()

def get_unprocessed_raw_signals(run_id: str, limit=None):
    conn = get_connection()
    cursor = conn.cursor()
    # Migration-safe: include both specific run_id and legacy NULL run_id
    cursor.execute("SELECT * FROM raw_signals WHERE filter_decision IS NULL AND (run_id = ? OR run_id IS NULL)", (run_id,))
    all_rows = cursor.fetchall()
    conn.close()
    
    if not all_rows:
        return []

    # Group by organization
    by_source = {}
    for row in all_rows:
        source_org = get_organization(None, row[2] or "unknown")
        by_source.setdefault(source_org, []).append(row)

    # Balance retrieval (e.g., max 20 per organization)
    max_per_org = 20
    balanced_rows = []
    
    logger.info(f"Sieve: Fetching balanced pool by organization for run {run_id}:")
    for org, rows in by_source.items():
        count = min(len(rows), max_per_org)
        balanced_rows.extend(rows[:count])
        logger.info(f" - {org}: {count} signals")
    
    # Apply limit after balancing if provided
    if limit:
        return balanced_rows[:limit]
    
    return balanced_rows

def update_signal_filter(url_hash: str, decision: str, reason: str, confidence: float = 0.0, scores=None, run_id: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE raw_signals 
    SET filter_decision = ?, filter_reason = ?, filter_confidence = ?, filter_scores = ?, filter_processed_at = datetime('now')
    WHERE url_hash = ? AND run_id = ?
    """, (decision, reason, confidence, json.dumps(scores) if scores else None, url_hash, run_id))
    conn.commit()
    conn.close()
...

def get_keep_signals(run_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    # Migration-safe: include both specific run_id and legacy NULL run_id
    cursor.execute("SELECT * FROM raw_signals WHERE filter_decision = 'KEEP' AND url_hash NOT IN (SELECT url FROM processed_signals WHERE run_id = ?) AND (run_id = ? OR run_id IS NULL)", (run_id, run_id))
    rows = cursor.fetchall()
    conn.close()
    return rows

def insert_processed_signal(title: str, url: str, score: float, topic_fingerprint: str, analysis_json: str, run_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO processed_signals (title, url, score, topic_fingerprint, analysis_json, reported_at, run_id)
    VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
    """, (title, url, score, topic_fingerprint, json.dumps(analysis_json), run_id))
    conn.commit()
    conn.close()

def get_top_scored_signals(limit=5, run_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if run_id:
        cursor.execute("SELECT * FROM processed_signals WHERE run_id = ? ORDER BY score DESC LIMIT ?", (run_id, limit))
    else:
        cursor.execute("SELECT * FROM processed_signals ORDER BY score DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows