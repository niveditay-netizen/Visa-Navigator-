import sqlite3
import os
from datetime import datetime

DB_PATH = "data/conversations.db"


def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role       TEXT,
            message    TEXT,
            timestamp  TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_turn(session_id: str, role: str, message: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO conversations (session_id, role, message, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, message, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


init_db()
