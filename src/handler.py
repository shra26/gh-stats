"""
handler.py -- AWS Lambda Function URL (payload format v2) entry point for gh-stats.

Parses the Lambda event, dispatches to router.route(), and builds a well-formed
HTTP response.  Always returns HTTP 200: on any error, an error-card SVG is
returned rather than a 5xx, so GitHub Camo never shows a broken-image icon.

Import convention: deployment root is src/; siblings imported without src. prefix.
"""

from __future__ import annotations

import logging
from typing import Any

import router
from common.cache import (
    CACHE_TTL,
    cache_control_header,
    resolve_cache_seconds,
)
from common.http_client import (
    GitHubError,
    GraphQLError,
    MaxRetriesError,
    NoTokensError,
)
from common.query_params import parse_int
from common.render_error import render_error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------

def _svg_response(
    svg: str,
    cache_seconds: int,
) -> dict[str, Any]:
    """Build a 200 Lambda response dict for an SVG payload."""
    return {
        "statusCode": 200,
        "headers": {
            "content-type": "image/svg+xml; charset=utf-8",
            "cache-control": cache_control_header(cache_seconds),
        },
        "body": svg,
        "isBase64Encoded": False,
    }


def _error_response(message: str, secondary: str = "") -> dict[str, Any]:
    """Return a 200 response carrying an error-card SVG, cached for error TTL."""
    svg = render_error(message, secondary)
    return _svg_response(svg, CACHE_TTL["error"]["default"])


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """AWS Lambda Function URL handler (payload format v2).

    Args:
        event: Lambda Function URL event dict.  Expected keys:
            ``rawPath`` -- request path (e.g. "/api").
            ``queryStringParameters`` -- decoded query string as str->str dict,
                or absent/None when no query string is present.
        context: Lambda context object (unused; present for compatibility).

    Returns:
        Lambda response dict with ``statusCode``, ``headers``, ``body``, and
        ``isBase64Encoded``.  Always 200; errors are returned as SVG cards.
    """
    raw_path: str = event.get("rawPath", "/")
    params: dict[str, str] = event.get("queryStringParameters") or {}

    # Parse optional caller-requested cache TTL before routing (needed on success).
    requested_cache_seconds: int | None = None
    raw_cache = params.get("cache_seconds")
    if raw_cache is not None:
        # parse_int signature: (val, default) -- use a sentinel default, then
        # re-examine to distinguish "absent" from "0".
        parsed = parse_int(raw_cache, -1)
        if parsed >= 0:
            requested_cache_seconds = parsed

    # ----- 404 for unknown paths -----
    # Route table KeyError = unknown path.  Detect before calling route() so we
    # can return a distinct error message without going through the generic
    # exception handler.
    from router import _ROUTES  # noqa: PLC0415 -- intentional late import to avoid cycles
    if raw_path not in _ROUTES:
        logger.warning("404 unknown path: %s", raw_path)
        return _error_response(
            f"Unknown endpoint: {raw_path}",
            "Valid endpoints: /api  /api/top-langs  /api/pin  /api/gist  /api/wakatime",
        )

    # ----- Dispatch -----
    try:
        svg, cache_key = router.route(raw_path, params)

    except (NoTokensError, MaxRetriesError) as exc:
        logger.error("Rate limit / no tokens: %s", exc, exc_info=True)
        return _error_response(
            "GitHub API rate limited, try later",
            "All available tokens are exhausted. Please try again in a few minutes.",
        )

    except ValueError as exc:
        logger.warning("Invalid request params: %s", exc)
        return _error_response(str(exc))

    except (GraphQLError, GitHubError) as exc:
        logger.error("GitHub API error: %s", exc, exc_info=True)
        return _error_response(
            "Something went wrong",
            str(exc)[:120],
        )

    except Exception as exc:  # noqa: BLE001 -- intentional catch-all for error card
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return _error_response(
            "Something went wrong",
            type(exc).__name__,
        )

    # ----- Build success response -----
    ttl_spec = CACHE_TTL[cache_key]
    effective_seconds = resolve_cache_seconds(
        requested_cache_seconds,
        default=ttl_spec["default"],
        min_=ttl_spec["min"],
        max_=ttl_spec["max"],
    )

    return _svg_response(svg, effective_seconds)
