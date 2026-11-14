"""
cookie_store.py

Persistent cookie jar for the collector.

The cookies from .env are only a seed: once the server sends updated cookies
(Set-Cookie headers), they are merged and saved to data/cookies.json, then reused
on the next run. If the .env value changes (manual refresh), the jar is reset
from the new seed.

Cookie values are never logged; only names, expiry dates and whether a value changed.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "cookies.json"


def _hash(value: str) -> str:
    """Return a short SHA-256 digest, used to compare secrets without storing them twice."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def parse_cookie_header(header: str) -> dict[str, str]:
    """Parse a raw "cookie" request header into a name -> value mapping.

    Args:
        header: Header value such as "a=1; b=2".

    Returns:
        A dict of cookie names to values.
    """
    cookies = {}
    for part in header.split(";"):
        name, sep, value = part.strip().partition("=")
        if sep and name:
            cookies[name] = value
    return cookies


def build_cookie_header(cookies: dict[str, str]) -> str:
    """Serialize a cookie mapping back into a "cookie" request header value.

    Args:
        cookies: Mapping of cookie names to values.

    Returns:
        The header value.
    """
    return "; ".join(f"{name}={value}" for name, value in cookies.items())


def parse_set_cookie(header: str) -> tuple[str, str, datetime | None]:
    """Parse one Set-Cookie response header.

    Args:
        header: Raw Set-Cookie header value.

    Returns:
        A (name, value, expires_at) tuple. expires_at is None for session cookies.
    """
    first, *attributes = header.split(";")
    name, _, value = first.strip().partition("=")
    expires_at = None
    for attribute in attributes:
        key, _, attr_value = attribute.strip().partition("=")
        key = key.lower()
        if key == "max-age":
            try:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(attr_value))
            except ValueError:
                logging.warning("Invalid Max-Age for cookie %s: %r", name, attr_value)
            break  # Max-Age takes precedence over Expires
        if key == "expires":
            try:
                expires_at = parsedate_to_datetime(attr_value)
            except (TypeError, ValueError):
                logging.warning("Invalid Expires for cookie %s: %r", name, attr_value)
    return name, value, expires_at


class CookieStore:
    """Cookie jar persisted to disk and seeded from the .env value.

    Attributes:
        cookies: Current mapping of cookie names to values.
    """

    def __init__(self, seed: str, path: Path = STORE_PATH) -> None:
        """Load the jar from disk, or from the seed if missing or outdated.

        Args:
            seed: Raw cookie header from .env.
            path: JSON file used for persistence.
        """
        self._path = path
        self._seed_hash = _hash(seed)
        self.cookies: dict[str, str] = {}

        stored = self._read()
        if stored and stored.get("seed_hash") == self._seed_hash:
            self.cookies = stored.get("cookies", {})
            logging.info(
                "Loaded %d cookies from store (last update: %s)",
                len(self.cookies),
                stored.get("updated_at"),
            )
        else:
            self.cookies = parse_cookie_header(seed)
            reason = "new seed in .env" if stored else "no store yet"
            logging.info("Cookie store initialised from .env (%s)", reason)
            self._write()

    def header(self) -> str:
        """Return the current cookies as a "cookie" request header value."""
        return build_cookie_header(self.cookies)

    def update(self, set_cookie_headers: list[str]) -> None:
        """Merge Set-Cookie headers from a response, log changes, and persist.

        Args:
            set_cookie_headers: Raw Set-Cookie header values.
        """
        if not set_cookie_headers:
            logging.info("Server sent no Set-Cookie header")
            return

        now = datetime.now(timezone.utc)
        for header in set_cookie_headers:
            name, value, expires_at = parse_set_cookie(header)
            if not name:
                continue
            expiry = expires_at.isoformat(timespec="seconds") if expires_at else "session"

            if expires_at is not None and expires_at <= now:
                self.cookies.pop(name, None)
                logging.info("Set-Cookie %s: deleted by server", name)
                continue

            previous = self.cookies.get(name)
            if previous is None:
                status = "new"
            elif previous == value:
                status = "same value"
            else:
                status = "value rotated"
            self.cookies[name] = value
            logging.info("Set-Cookie %s: %s, expires %s", name, status, expiry)

        self._write()

    def _read(self) -> dict | None:
        """Read the store file, returning None if absent or unreadable."""
        if not self._path.exists():
            return None
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logging.warning("Cookie store unreadable, reseeding from .env: %s", exc)
            return None

    def _write(self) -> None:
        """Persist the jar to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "seed_hash": self._seed_hash,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cookies": self.cookies,
        }
        try:
            self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            logging.exception("Could not write cookie store")
