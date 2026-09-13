import sqlite3
import os

def get_db_path() -> str:
    """Return the configured SQLite path at call time."""
    return os.environ.get("SIGNALS_DB_PATH", "data/signals.db")


def get_connection():
    return sqlite3.connect(get_db_path())

def init_db():
    db_path = get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
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
        filter_processed_at TEXT,
        url TEXT,
        run_id TEXT
    )
    """)
    try:
        cursor.execute("ALTER TABLE raw_signals ADD COLUMN run_id TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Processed signals table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        url TEXT,
        score REAL,
        topic_fingerprint TEXT,
        analysis_json TEXT,
        reported_at TEXT,
        run_id TEXT
    )
    """)
    try:
        cursor.execute("ALTER TABLE processed_signals ADD COLUMN run_id TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_raw_run_decision "
        "ON raw_signals(run_id, filter_decision)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_raw_source_found "
        "ON raw_signals(source_id, found_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_processed_run_score "
        "ON processed_signals(run_id, score)"
    )
    
    conn.commit()
    conn.close()
