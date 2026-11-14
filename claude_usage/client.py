"""
client.py

HTTP client for the (unofficial) claude.ai usage endpoint.
Uses curl_cffi to impersonate a real Chrome browser so Cloudflare accepts the request.
"""

import logging

from curl_cffi import requests

USAGE_URL_TEMPLATE = "https://claude.ai/api/organizations/{org_id}/usage"
REQUEST_TIMEOUT_SECONDS = 30
BROWSER_IMPERSONATION = "chrome"


class AuthenticationError(Exception):
    """Raised when claude.ai rejects the session cookies (expired or invalid)."""


class FetchError(Exception):
    """Raised when the usage data cannot be retrieved for any other reason."""


def fetch_usage(org_id: str, cookies: str) -> tuple[dict, list[str]]:
    """Fetch the current usage data for an organization.

    Args:
        org_id: claude.ai organization UUID.
        cookies: Raw "cookie" header value from a logged-in browser session.

    Returns:
        A (payload, set_cookie_headers) tuple: the decoded JSON returned by
        claude.ai and the raw Set-Cookie headers of the response.

    Raises:
        AuthenticationError: If the session is expired or invalid (HTTP 401/403).
        FetchError: On network errors, other HTTP errors, or invalid JSON.
    """
    url = USAGE_URL_TEMPLATE.format(org_id=org_id)
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "anthropic-client-platform": "web_claude_ai",
        "referer": "https://claude.ai/new",
        "cookie": cookies,
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            impersonate=BROWSER_IMPERSONATION,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestsError as exc:
        raise FetchError(f"Network error: {exc}") from exc

    set_cookie_headers = response.headers.get_list("set-cookie")

    if response.status_code in (401, 403):
        raise AuthenticationError(
            f"HTTP {response.status_code}: session rejected (cookies expired or blocked)"
        )
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code}: {response.text[:200]}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise FetchError(f"Invalid JSON response: {response.text[:200]}") from exc

    logging.debug("Usage payload: %s", payload)
    return payload, set_cookie_headers
