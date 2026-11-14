"""
collector.py

One complete collection run: load settings, fetch usage, store it, update
cookies, and report failures/recoveries to Discord.

Shared by the scheduled task (python -m claude_usage) and the dashboard's
refresh button.
"""

import logging
import sqlite3
from dataclasses import dataclass

from .client import AuthenticationError, FetchError, fetch_usage
from .config import ConfigError, load_settings
from .cookie_store import CookieStore
from .notifier import report_failure, report_success
from .storage import extract_windows, save_snapshot


@dataclass(frozen=True)
class CollectResult:
    """Outcome of a collection run.

    Attributes:
        ok: True if a snapshot was saved.
        message: Short French message suitable for display to the user.
    """

    ok: bool
    message: str


def run_collection() -> CollectResult:
    """Run one collection and report the outcome.

    Returns:
        A CollectResult describing success or failure. Never raises for
        expected failures (config, auth, network, database).
    """
    try:
        settings = load_settings()
    except ConfigError as exc:
        logging.error("Configuration error: %s", exc)
        return _fail("config", f"configuration invalide ({exc}). Vérifiez le fichier `.env`.")

    store = CookieStore(settings.cookies)
    try:
        payload, set_cookie_headers = fetch_usage(settings.org_id, store.header())
        store.update(set_cookie_headers)
        snapshot_id = save_snapshot(payload)
    except AuthenticationError as exc:
        logging.error("%s. Refresh CLAUDE_COOKIES in .env.", exc)
        return _fail(
            "auth",
            "session refusée par claude.ai (cookies expirés ?). "
            "Mettez à jour `CLAUDE_COOKIES` dans `.env`.",
        )
    except FetchError as exc:
        logging.error("Fetch failed: %s", exc)
        return _fail("fetch", f"échec de la récupération des données : `{exc}`")
    except sqlite3.Error as exc:
        logging.exception("Could not save snapshot")
        return _fail("database", f"impossible d'enregistrer le relevé : `{exc}`")

    report_success()
    windows = extract_windows(payload)
    summary = ", ".join(f"{name}={util}%" for name, util, _ in windows)
    logging.info("Snapshot #%d saved: %s", snapshot_id, summary or "no usage window found")
    return CollectResult(ok=True, message="Relevé effectué.")


def _fail(kind: str, message: str) -> CollectResult:
    """Report a failure to Discord and build the corresponding result."""
    report_failure(kind, message)
    return CollectResult(ok=False, message=f"Échec : {message}")
