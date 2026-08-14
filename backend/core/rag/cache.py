"""Semantic answer cache, partitioned by vessel scope.

The partition is the important part. Two users can ask a near-identical question
and require different answers, because the applicability filter gave their
questions different clause sets. Serving one user's cached answer to another
vessel would produce a confidently wrong answer carrying a valid citation —
precisely the failure the context layer exists to prevent. `scope_key` makes
that impossible: a cache entry is only ever reachable from an identical vessel
scope.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "query_cache.db"

# Bump when the prompt, the output format or the applicability logic changes, so
# answers produced by an older pipeline are never served by a newer one.
# Engine version. Semantic, and public: it is written into every provenance
# record and shown in the UI, so it must mean something to an auditor a year
# from now rather than describing whatever bug was last fixed.
#
# Bump MINOR when a change alters the answers the engine produces — prompt,
# model, retrieval or filtering. Bump PATCH for changes that cannot. Any bump
# partitions the cache, so entries from an older engine are never served under a
# newer one.
#
# 3.2.0 — NOT_REQUIRED verdicts are downgraded to CONDITIONAL when the exemption
#         relied on carries transitional or conditional language. Observed in the
#         wild: a transitional exemption for "existing vessels transitioning from
#         MGN 280" was reported as a general exemption. Changes verdicts.
# 3.1.1 — citation verification now accepts clause numbers that appear inside
#         retrieved statute (cross-references such as "the requirements of
#         5.6.1"). Answers are unchanged, but the recorded verified flag is not,
#         so cached entries carrying the old flag must not be served.
# 3.1.0 — excluded clause identifiers withheld from the prompt; machine-readable
#         verdict line added; generation moved to the Gemini 3.x line.
PIPELINE_VERSION = "3.2.0"

NO_VESSEL_SCOPE = "no-vessel"


def scope_key(vessel, code_ids=None, mode: str = "ask") -> str:
    """Stable identity for a vessel's applicability scope and corpus set.

    Only the attributes that can change which clauses are retrieved take part.
    Hull material is included because it is part of the locked state shown to
    the model and can change the wording of an answer. The corpus set and mode
    are included because the same question against SPVC alone, against SPVC and
    WBC3 blended, and in comparison mode are three different questions with
    three different correct answers.
    """
    corpora = ",".join(sorted(code_ids)) if code_ids else "all"
    if vessel is None:
        return f"{PIPELINE_VERSION}|{mode}|{corpora}|{NO_VESSEL_SCOPE}"
    return (
        f"{PIPELINE_VERSION}|{mode}|{corpora}"
        f"|{vessel.vessel_type}|{vessel.length_overall}"
        f"|{vessel.area_category}|{vessel.hull_material}|{vessel.passenger_count}"
    )


def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_key TEXT NOT NULL,
            question TEXT NOT NULL,
            embedding BLOB NOT NULL,
            answer TEXT NOT NULL,
            sources TEXT NOT NULL,
            filtered_out TEXT NOT NULL DEFAULT '[]',
            verified INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    # The schema check MUST come before the index. On a pre-context-layer
    # database the CREATE TABLE above is a no-op (the table already exists with
    # the old shape), so indexing scope_key would raise "no such column" before
    # the migration ever ran.
    columns = {row[1] for row in conn.execute("PRAGMA table_info(cache)")}
    if "scope_key" not in columns:
        # Rows predating the context layer were computed without applicability
        # filtering and must never be served under the new pipeline. Rebuild
        # rather than migrate — it is a cache, so there is nothing to preserve.
        conn.execute("DROP TABLE cache")
        conn.commit()
        conn.close()
        return _get_conn()

    conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_scope ON cache (scope_key)")
    return conn


def find_similar(embedding: np.ndarray, scope_key: str, threshold: float = 0.92):
    """Nearest cached answer within the same vessel scope, or None."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, question, embedding, answer, sources, verified, created_at, filtered_out "
        "FROM cache WHERE scope_key = ?",
        (scope_key,),
    ).fetchall()
    conn.close()

    if not rows:
        return None

    best = None
    best_score = -1.0
    query_norm = np.linalg.norm(embedding)
    if np.isclose(query_norm, 0):
        return None

    for row in rows:
        cached_embedding = np.frombuffer(row[2], dtype=np.float32)
        if cached_embedding.shape[0] != embedding.shape[0]:
            continue  # entry cached under a different embedding model
        cached_norm = np.linalg.norm(cached_embedding)
        if np.isclose(cached_norm, 0):
            continue
        score = float(np.dot(embedding, cached_embedding) / (query_norm * cached_norm))
        if score > best_score:
            best_score = score
            best = row

    if best is not None and best_score >= threshold:
        return {
            "question": best[1],
            "answer": best[3],
            "sources": json.loads(best[4]),
            "verified": bool(best[5]),
            "similarity": best_score,
            "cached_at": best[6],
            "filtered_out": json.loads(best[7]),
        }
    return None


def store(
    question: str,
    embedding: np.ndarray,
    answer: str,
    sources: list,
    filtered_out: list,
    verified: bool,
    scope_key: str,
):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO cache "
        "(scope_key, question, embedding, answer, sources, filtered_out, verified, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            scope_key,
            question,
            embedding.astype(np.float32).tobytes(),
            answer,
            json.dumps(sources),
            json.dumps(filtered_out),
            int(verified),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()
