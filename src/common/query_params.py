"""
query_params.py -- query-string parsing and validation utilities.

All functions operate on raw string values as received from Lambda event
queryStringParameters (or None when a param is absent).

Import convention: deployment root is src/; siblings imported without src. prefix.
"""

from __future__ import annotations

import os
import re


# ---------------------------------------------------------------------------
# Primitive coercions
# ---------------------------------------------------------------------------

def parse_bool(val: str | None, default: bool = False) -> bool:
    """
    Coerce a query-string value to bool.

    - "true"  (case-insensitive) -> True
    - "false" (case-insensitive) -> False
    - None / missing / anything else -> *default*
    """
    if val is None:
        return default
    lower = val.strip().lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    return default


def parse_array(val: str | None) -> list[str]:
    """
    Split a comma-separated query-string value into a list of stripped strings.

    Empty strings and whitespace-only tokens are dropped.
    Returns [] if *val* is None or empty.
    """
    if not val:
        return []
    return [item.strip() for item in val.split(",") if item.strip()]


def parse_int(val: str | None, default: int) -> int:
    """
    Parse *val* as an integer, returning *default* on any failure.
    """
    if val is None:
        return default
    try:
        return int(val.strip())
    except (ValueError, AttributeError):
        return default


# ---------------------------------------------------------------------------
# Username validation
# ---------------------------------------------------------------------------

# GitHub username rules:
#   - 1 to 39 characters
#   - alphanumeric or single hyphens
#   - cannot start or end with a hyphen
_USERNAME_RE = re.compile(
    r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$"
)


def is_valid_username(username: str | None) -> bool:
    """
    Return True if *username* matches the GitHub username format.

    Also used for gist owner validation.  Returns False for None or empty string.
    """
    if not username:
        return False
    return bool(_USERNAME_RE.match(username))


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------

def _load_whitelist() -> list[str] | None:
    """
    Read GH_WHITELIST from the environment at module import time.

    Returns a list of lowercased usernames, or None if the variable is unset
    or empty (meaning "allow all", for development).
    """
    raw = os.environ.get("GH_WHITELIST", "").strip()
    if not raw:
        return None
    return [u.strip().lower() for u in raw.split(",") if u.strip()]


WHITELIST: list[str] | None = _load_whitelist()


def is_whitelisted(username: str | None) -> bool:
    """
    Return True if *username* is allowed to be served.

    - WHITELIST is None (env var unset): allow all users (development mode).
    - WHITELIST is a list: case-insensitive membership check.
    - None / empty username: False.
    """
    if WHITELIST is None:
        return True
    if not username:
        return False
    return username.lower() in WHITELIST
