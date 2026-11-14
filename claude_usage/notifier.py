"""
notifier.py

Discord webhook alerts for collection failures.

To avoid spamming, an alert is sent only when the collection starts failing
(or the kind of failure changes), and a recovery message when it works again.
The current alert state is persisted in data/alert_state.json.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from curl_cffi import requests

from .config import get_discord_webhook_url

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "alert_state.json"
REQUEST_TIMEOUT_SECONDS = 10
MESSAGE_PREFIX = "**ClaudeUsage**"


def _read_state(path: Path) -> dict:
    """Read the alert state, defaulting to 'not failing'."""
    if not path.exists():
        return {"failing": False}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logging.warning("Alert state unreadable, resetting: %s", exc)
        return {"failing": False}


def _write_state(state: dict, path: Path) -> None:
    """Persist the alert state."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        logging.exception("Could not write alert state")


def send_discord_message(content: str) -> bool:
    """Post a message to the configured Discord webhook.

    Never raises: failures are logged so they cannot break the collection.

    Args:
        content: Message text (Discord markdown, max 2000 characters).

    Returns:
        True if the message was accepted, False otherwise (or if no webhook is set).
    """
    url = get_discord_webhook_url()
    if not url:
        logging.debug("No Discord webhook configured, alert not sent")
        return False
    try:
        response = requests.post(
            url, json={"content": content[:2000]}, timeout=REQUEST_TIMEOUT_SECONDS
        )
    except requests.RequestsError as exc:
        logging.error("Discord webhook unreachable: %s", exc)
        return False
    if response.status_code >= 300:
        logging.error("Discord webhook rejected message: HTTP %d", response.status_code)
        return False
    logging.info("Discord alert sent")
    return True


def report_failure(kind: str, message: str, path: Path = STATE_PATH) -> None:
    """Record a failure and alert Discord if it is new or of a different kind.

    Args:
        kind: Short failure category (e.g. "auth", "fetch", "config", "database").
        message: Text shown to the user in Discord (French).
        path: Alert state file.
    """
    state = _read_state(path)
    if state.get("failing") and state.get("kind") == kind:
        logging.info("Failure '%s' already reported, no new alert", kind)
        return

    sent = send_discord_message(f"🔴 {MESSAGE_PREFIX} : {message}")
    if not sent and get_discord_webhook_url():
        return  # Keep state unchanged so the alert is retried next time
    _write_state(
        {
            "failing": True,
            "kind": kind,
            "since": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        path,
    )


def report_success(path: Path = STATE_PATH) -> None:
    """Record a successful collection and alert Discord if it recovers from a failure.

    Args:
        path: Alert state file.
    """
    state = _read_state(path)
    if not state.get("failing"):
        return
    send_discord_message(
        f"🟢 {MESSAGE_PREFIX} : la collecte fonctionne à nouveau "
        f"(en échec depuis {state.get('since', '?')} UTC)."
    )
    _write_state({"failing": False}, path)
