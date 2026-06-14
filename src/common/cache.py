# common/cache.py -- per-card TTL table and Cache-Control header builder.
# Import as: from common.cache import CACHE_TTL, resolve_cache_seconds, cache_control_header

from __future__ import annotations

import os

import config

# Per-card TTL bounds (seconds).
# Keys match the card identifiers used in router.py / handler.py.
CACHE_TTL: dict[str, dict[str, int]] = {
    "stats": {
        "default": 86400,
        "min": 43200,
        "max": 172800,
    },
    "top-langs": {
        "default": 518400,
        "min": 172800,
        "max": 864000,
    },
    "pin": {
        "default": 864000,
        "min": 86400,
        "max": 864000,
    },
    "gist": {
        "default": 172800,
        "min": 86400,
        "max": 864000,
    },
    "wakatime": {
        "default": 86400,
        "min": 43200,
        "max": 172800,
    },
    "error": {
        "default": 600,
        "min": 600,
        "max": 600,
    },
}


def resolve_cache_seconds(
    requested: int | None,
    default: int,
    min_: int,
    max_: int,
) -> int:
    """Return the effective cache TTL in seconds.

    Resolution logic:
    1. Start from ``requested`` (caller-supplied query param), clamped to
       ``[min_, max_]``.  If ``requested`` is ``None``, use ``default``.
    2. If the env var ``config.CACHE_SECONDS_ENV`` is set, its integer value
       overrides the result unconditionally (matching the original
       github-readme-stats behaviour where the global env var bypasses the
       per-card clamp).

    Args:
        requested: The ``cache_seconds`` query-string value, or ``None`` if
            the caller did not supply it.
        default: Per-card default TTL (e.g. 86400).
        min_: Per-card minimum TTL.
        max_: Per-card maximum TTL.

    Returns:
        Effective cache duration in seconds (always >= 0).
    """
    if requested is None:
        seconds = default
    else:
        seconds = max(min_, min(requested, max_))

    global_override: str | None = os.environ.get(config.CACHE_SECONDS_ENV)
    if global_override is not None:
        try:
            seconds = int(global_override)
        except ValueError:
            pass  # Malformed override; keep the clamped value.

    return max(0, seconds)


def cache_control_header(seconds: int) -> str:
    """Build a ``Cache-Control`` header value for the given TTL.

    Args:
        seconds: TTL in seconds.  Values < 1 result in a no-cache directive.

    Returns:
        A ready-to-use ``Cache-Control`` header value string.
    """
    if seconds < 1:
        return "no-cache, no-store, must-revalidate"
    return f"max-age={seconds}, s-maxage={seconds}, stale-while-revalidate=86400"
