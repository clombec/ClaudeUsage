"""
config.py

Loads collector settings from environment variables (and the .env file).
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
DEFAULT_POLL_INTERVAL_SECONDS = 3600


class ConfigError(Exception):
    """Raised when a required setting is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the collector.

    Attributes:
        org_id: claude.ai organization UUID.
        cookies: Raw "cookie" header value used to authenticate.
        poll_interval_seconds: Delay between two fetches in loop mode.
    """

    org_id: str
    cookies: str
    poll_interval_seconds: int


def get_discord_webhook_url() -> str | None:
    """Return the Discord webhook URL from the environment, if configured.

    Returns:
        The webhook URL, or None if DISCORD_WEBHOOK_URL is unset or empty.
    """
    load_dotenv(ENV_PATH)
    return os.environ.get("DISCORD_WEBHOOK_URL", "").strip() or None


def load_settings() -> Settings:
    """Read settings from the environment, loading .env first if present.

    Returns:
        A populated Settings instance.

    Raises:
        ConfigError: If a required variable is missing or invalid.
    """
    load_dotenv(ENV_PATH)

    org_id = os.environ.get("CLAUDE_ORG_ID", "").strip()
    cookies = os.environ.get("CLAUDE_COOKIES", "").strip()
    if not org_id:
        raise ConfigError("CLAUDE_ORG_ID is not set")
    if not cookies:
        raise ConfigError("CLAUDE_COOKIES is not set")

    raw_interval = os.environ.get("POLL_INTERVAL_SECONDS", str(DEFAULT_POLL_INTERVAL_SECONDS))
    try:
        interval = int(raw_interval)
    except ValueError as exc:
        raise ConfigError(f"POLL_INTERVAL_SECONDS is not an integer: {raw_interval!r}") from exc
    if interval < 60:
        raise ConfigError("POLL_INTERVAL_SECONDS must be at least 60")

    return Settings(org_id=org_id, cookies=cookies, poll_interval_seconds=interval)
