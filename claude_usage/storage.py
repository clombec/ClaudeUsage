"""
storage.py

SQLite persistence for usage snapshots.
Stores the raw JSON payload plus one flattened row per usage window
(e.g. five_hour, seven_day) for easy querying.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "usage.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_at TEXT NOT NULL,
    raw_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usage_windows (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    window TEXT NOT NULL,
    utilization REAL,
    resets_at TEXT,
    PRIMARY KEY (snapshot_id, window)
);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    """Open the database, creating the file and schema if needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def extract_windows(payload: dict) -> list[tuple[str, float | None, str | None]]:
    """Extract usage windows from the payload.

    Any top-level key whose value is an object containing "utilization"
    is treated as a usage window.

    Args:
        payload: Decoded JSON from the usage endpoint.

    Returns:
        A list of (window_name, utilization, resets_at) tuples.
    """
    windows = []
    for key, value in payload.items():
        if isinstance(value, dict) and "utilization" in value:
            windows.append((key, value.get("utilization"), value.get("resets_at")))
    return windows


def save_snapshot(payload: dict, db_path: Path = DB_PATH) -> int:
    """Persist a usage snapshot.

    Args:
        payload: Decoded JSON from the usage endpoint.
        db_path: SQLite file path. Defaults to data/usage.sqlite3.

    Returns:
        The id of the inserted snapshot row.

    Raises:
        sqlite3.Error: If the database cannot be written.
    """
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = _connect(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO snapshots (fetched_at, raw_json) VALUES (?, ?)",
                (fetched_at, json.dumps(payload, ensure_ascii=False)),
            )
            snapshot_id = cursor.lastrowid
            conn.executemany(
                "INSERT INTO usage_windows (snapshot_id, window, utilization, resets_at) "
                "VALUES (?, ?, ?, ?)",
                [(snapshot_id, *window) for window in extract_windows(payload)],
            )
    finally:
        conn.close()
    return snapshot_id
