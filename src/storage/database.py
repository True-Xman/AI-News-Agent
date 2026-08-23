import sqlite3
import os

DB_PATH = "data/signals.db"

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Sources table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        url TEXT,
        type TEXT,
        priority INTEGER,
        category TEXT
    )
    """)
    
    # Raw signals table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw_signals (
        url_hash TEXT PRIMARY KEY,
        title TEXT,
        source TEXT,
        source_id INTEGER,
        found_at REAL,
        snippet TEXT,
        filter_decision TEXT,
        filter_reason TEXT,
        filter_confidence REAL,
        filter_scores TEXT,
        filter_processed_at TEXT
    )
    """)
    
    # Processed signals table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        url TEXT,
        score REAL,
        topic_fingerprint TEXT,
        analysis_json TEXT,
        reported_at TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)