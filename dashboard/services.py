"""
services.py

Business logic for the dashboard: reads usage snapshots written by the collector.
"""

import logging
from datetime import datetime, timedelta, timezone

from django.db import DatabaseError, connection

from claude_usage.collector import CollectResult, run_collection

FIVE_HOUR = "five_hour"
SEVEN_DAY = "seven_day"
EXTRA_USAGE = "extra_usage"
CHART_WINDOWS = (FIVE_HOUR, SEVEN_DAY, EXTRA_USAGE)

SERIES_QUERY = """
SELECT s.fetched_at, w.window, w.utilization, w.resets_at
FROM usage_windows w
JOIN snapshots s ON s.id = w.snapshot_id
WHERE s.fetched_at >= %s
ORDER BY s.fetched_at
"""


def get_usage_series(days: int | None) -> dict:
    """Return usage points per window for the given period.

    Args:
        days: Number of past days to include, or None for the whole history.

    Returns:
        A dict with:
            series: mapping of window name to a list of {"x": iso_utc, "y": percent}.
            show_extra: True if extra usage exceeds 0 at least once in the period.
            latest: mapping of window name to {"utilization", "resets_at", "fetched_at"}
                for the most recent point, with datetimes parsed (UTC).
    """
    cutoff = ""
    if days is not None:
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff = cutoff_dt.isoformat(timespec="seconds")

    try:
        with connection.cursor() as cursor:
            cursor.execute(SERIES_QUERY, [cutoff])
            rows = cursor.fetchall()
    except DatabaseError as exc:
        logging.error("Could not read usage data: %s", exc)
        rows = []

    series: dict[str, list[dict]] = {window: [] for window in CHART_WINDOWS}
    latest: dict[str, dict] = {}
    for fetched_at, window, utilization, resets_at in rows:
        if window not in series:
            continue
        series[window].append({"x": fetched_at, "y": utilization})
        latest[window] = {
            "utilization": utilization,
            "resets_at": _parse_iso(resets_at),
            "fetched_at": _parse_iso(fetched_at),
        }

    show_extra = any((point["y"] or 0) > 0 for point in series[EXTRA_USAGE])
    return {"series": series, "show_extra": show_extra, "latest": latest}


def trigger_collection() -> CollectResult:
    """Run an immediate, one-off collection (same logic as the scheduled task).

    Does not affect the hourly schedule, which runs independently.

    Returns:
        The collection outcome, with a French message for the user.
    """
    logging.info("Manual refresh requested from dashboard")
    return run_collection()


def _parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO 8601 string (accepting a trailing 'Z'), or return None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        logging.warning("Invalid ISO datetime: %r", value)
        return None
