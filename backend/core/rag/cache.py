import sqlite3
import json
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "query_cache.db"

def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            embedding BLOB NOT NULL,
            answer TEXT NOT NULL,
            sources TEXT NOT NULL,
            verified INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    return conn

def find_similar(embedding: np.ndarray, threshold: float = 0.92):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, question, embedding, answer, sources, verified, created_at FROM cache"
    ).fetchall()
    conn.close()

    if not rows:
        return None

    best = None
    best_score = -1
    query_norm = np.linalg.norm(embedding)

    for row in rows:
        cached_embedding = np.frombuffer(row[2], dtype=np.float32)
        score = float(np.dot(embedding, cached_embedding) / (query_norm * np.linalg.norm(cached_embedding)))
        if score > best_score:
            best_score = score
            best = row

    if best_score >= threshold:
        return {
            "question": best[1],
            "answer": best[3],
            "sources": json.loads(best[4]),
            "verified": bool(best[5]),
            "similarity": best_score,
            "cached_at": best[6],
        }
    return None

def store(question: str, embedding: np.ndarray, answer: str, sources: list, verified: bool):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO cache (question, embedding, answer, sources, verified, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            question,
            embedding.astype(np.float32).tobytes(),
            answer,
            json.dumps(sources),
            int(verified),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()