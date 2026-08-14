import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "usage.db"
MONTHLY_LIMIT = 20  # beta cap per user — raise this once you're on a production Cohere key

def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            user_id TEXT NOT NULL,
            month TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, month)
        )
    """)
    return conn

def _current_month():
    return datetime.now(timezone.utc).strftime("%Y-%m")

def check_and_increment(user_id: str) -> tuple[bool, int]:
    """Returns (allowed, remaining_after_this_call)."""
    month = _current_month()
    conn = _get_conn()
    row = conn.execute(
        "SELECT count FROM usage WHERE user_id = ? AND month = ?", (user_id, month)
    ).fetchone()
    current = row[0] if row else 0

    if current >= MONTHLY_LIMIT:
        conn.close()
        return False, 0

    new_count = current + 1
    conn.execute(
        "INSERT INTO usage (user_id, month, count) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, month) DO UPDATE SET count = ?",
        (user_id, month, new_count, new_count),
    )
    conn.commit()
    conn.close()
    return True, MONTHLY_LIMIT - new_count

# ── Public demo budget ─────────────────────────────────────────────────────
#
# The demo is un-gated, so there is no per-user identity to meter against.
# Instead a single shared daily budget caps total exposure: worst case is
# DEMO_DAILY_LIMIT generations per day regardless of how much traffic arrives.
# Cheap to reason about, and it satisfies the zero-cost-risk constraint —
# maximum spend is a known number, not a function of how well the link spreads.

DEMO_DAILY_LIMIT = 200
_DEMO_USER = "__public_demo__"


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def check_and_increment_demo() -> tuple[bool, int]:
    """Returns (allowed, remaining_today) for the shared public demo budget."""
    day = _today()
    conn = _get_conn()
    row = conn.execute(
        "SELECT count FROM usage WHERE user_id = ? AND month = ?", (_DEMO_USER, day)
    ).fetchone()
    current = row[0] if row else 0

    if current >= DEMO_DAILY_LIMIT:
        conn.close()
        return False, 0

    new_count = current + 1
    conn.execute(
        "INSERT INTO usage (user_id, month, count) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, month) DO UPDATE SET count = ?",
        (_DEMO_USER, day, new_count, new_count),
    )
    conn.commit()
    conn.close()
    return True, DEMO_DAILY_LIMIT - new_count


def demo_remaining() -> int:
    conn = _get_conn()
    row = conn.execute(
        "SELECT count FROM usage WHERE user_id = ? AND month = ?", (_DEMO_USER, _today())
    ).fetchone()
    conn.close()
    return DEMO_DAILY_LIMIT - (row[0] if row else 0)
