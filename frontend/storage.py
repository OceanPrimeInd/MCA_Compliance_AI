import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "conversations.db"

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            messages TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    return conn

def save_conversation(conv_id: str, title: str, messages: list):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO conversations (id, title, messages, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET title=excluded.title, messages=excluded.messages, updated_at=excluded.updated_at",
        (conv_id, title, json.dumps(messages), datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()

def list_conversations():
    conn = _get_conn()
    rows = conn.execute("SELECT id, title, updated_at FROM conversations ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "updated_at": r[2]} for r in rows]

def load_conversation(conv_id: str):
    conn = _get_conn()
    row = conn.execute("SELECT messages FROM conversations WHERE id=?", (conv_id,)).fetchone()
    conn.close()
    return json.loads(row[0]) if row else []

def delete_conversation(conv_id: str):
    conn = _get_conn()
    conn.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
    conn.commit()
    conn.close()