import hashlib
from .database import get_connection
from ..models.raw_signal import RawSignal
import json

def insert_raw_signal(signal: RawSignal):
    conn = get_connection()
    cursor = conn.cursor()
    url_hash = hashlib.md5(signal.url.encode()).hexdigest()
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO raw_signals (url_hash, title, source, source_id, found_at, snippet)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (url_hash, signal.title, signal.source, signal.source_id, signal.found_at, signal.snippet))
        conn.commit()
    finally:
        conn.close()

def get_unprocessed_raw_signals(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM raw_signals WHERE filter_decision IS NULL LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    # Simplified mapping
    return rows

def update_signal_filter(url_hash, decision, reason, confidence=0.0, scores=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE raw_signals 
    SET filter_decision = ?, filter_reason = ?, filter_confidence = ?, filter_scores = ?, filter_processed_at = datetime('now')
    WHERE url_hash = ?
    """, (decision, reason, confidence, json.dumps(scores) if scores else None, url_hash))
    conn.commit()
    conn.close()

def get_keep_signals():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM raw_signals WHERE filter_decision = 'KEEP' AND url_hash NOT IN (SELECT url FROM processed_signals)")
    rows = cursor.fetchall()
    conn.close()
    return rows

def insert_processed_signal(title, url, score, topic_fingerprint, analysis_json):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO processed_signals (title, url, score, topic_fingerprint, analysis_json, reported_at)
    VALUES (?, ?, ?, ?, ?, datetime('now'))
    """, (title, url, score, topic_fingerprint, json.dumps(analysis_json)))
    conn.commit()
    conn.close()

def get_top_scored_signals(limit=5):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM processed_signals ORDER BY score DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows