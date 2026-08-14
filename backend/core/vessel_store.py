"""Persistence for verified vessel profiles.

One profile per user for now. SQLite, matching the pattern already used by
core.usage and core.rag.cache. When the designer workflow arrives — an architect
working across several unbuilt vessels at once — this becomes one row per
project and `get_profile` takes a project id.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core.vessel import VesselProfile

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "vessels.db"


def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vessel_profiles (
            user_id TEXT PRIMARY KEY,
            vessel_type TEXT NOT NULL,
            length_overall REAL NOT NULL,
            area_category INTEGER NOT NULL,
            hull_material TEXT NOT NULL,
            passenger_count INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    return conn


def save_profile(user_id: str, profile: VesselProfile) -> None:
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO vessel_profiles
            (user_id, vessel_type, length_overall, area_category,
             hull_material, passenger_count, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            vessel_type = excluded.vessel_type,
            length_overall = excluded.length_overall,
            area_category = excluded.area_category,
            hull_material = excluded.hull_material,
            passenger_count = excluded.passenger_count,
            updated_at = excluded.updated_at
        """,
        (
            user_id,
            profile.vessel_type,
            profile.length_overall,
            profile.area_category,
            profile.hull_material,
            profile.passenger_count,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_profile(user_id: str) -> VesselProfile | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT vessel_type, length_overall, area_category, hull_material, passenger_count "
        "FROM vessel_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return VesselProfile(
        vessel_type=row[0],
        length_overall=row[1],
        area_category=row[2],
        hull_material=row[3],
        passenger_count=row[4],
    )


def delete_profile(user_id: str) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM vessel_profiles WHERE user_id = ?", (user_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted
