from pathlib import Path
import sqlite3
from typing import Optional

def get_db_connection(db_path: Path) -> sqlite3.Connection:
    """Get a database connection with proper settings"""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db(db_path):
    """Initialize all database tables"""
    with sqlite3.connect(db_path) as conn:
        # API Keys table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                api_key TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Secrets table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS secrets (
                service_name TEXT PRIMARY KEY,
                encrypted_data BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Master key table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS master_key (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                key BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()  # Commit all table creations at once