"""
router.py -- path-to-handler dispatch table for gh-stats.

Each route handler validates required params, checks the username allowlist
and format, wraps the fetch in PAT rotation, and delegates rendering to the
matching card module.

Import convention: deployment root is src/; siblings imported without src. prefix.
"""

from __future__ import annotations

from typing import Callable

from common.cache import CACHE_TTL
from common.query_params import (
    is_valid_username,
    is_whitelisted,
    parse_array,
    parse_bool,
    parse_int,
)
from common.retryer import retry_with_pat_rotation
from fetchers.gist_fetcher import fetch_gist
from fetchers.repo_fetcher import fetch_repo
from fetchers.stats_fetcher import fetch_stats
from fetchers.top_langs_fetcher import fetch_top_languages
from fetchers.wakatime_fetcher import fetch_wakatime
from cards.gist_card import render_gist_card
from cards.repo_card import render_repo_card
from cards.stats_card import render_stats_card
from cards.top_langs_card import render_top_languages_card
from cards.wakatime_card import render_wakatime_card


# ---------------------------------------------------------------------------
# Private validation helper
# ---------------------------------------------------------------------------

def _validate_username(username: str | None, param_name: str = "username") -> str:
    """Raise ValueError if username is absent, malformed, or not allowlisted."""
    if not username:
        raise ValueError(f"Missing required parameter: {param_name}")
    if not is_valid_username(username):
        raise ValueError(
            f"Invalid {param_name} '{username}': must be 1-39 alphanumeric"
            " characters or hyphens, not starting or ending with a hyphen."
        )
    if not is_whitelisted(username):
        raise ValueError(
            f"Username '{username}' is not allowed on this instance."
        )
    return username


# ---------------------------------------------------------------------------
# Per-route handlers
# Each returns (svg: str, cache_key: str).
# ---------------------------------------------------------------------------

def _route_stats(params: dict[str, str]) -> tuple[str, str]:
    username = _validate_username(params.get("username"))

    include_all_commits = parse_bool(params.get("include_all_commits"))
    exclude_repo = parse_array(params.get("exclude_repo"))

    data = retry_with_pat_rotation(
        lambda token: fetch_stats(
            username,
            include_all_commits=include_all_commits,
            exclude_repo=exclude_repo,
            token=token,
        )
    )

    svg = render_stats_card(data, options=params)
    return svg, "stats"


def _route_top_langs(params: dict[str, str]) -> tuple[str, str]:
    username = _validate_username(params.get("username"))

    exclude_repo = parse_array(params.get("exclude_repo"))
    size_weight = float(parse_int(params.get("size_weight"), 1))
    count_weight = float(parse_int(params.get("count_weight"), 0))

    data = retry_with_pat_rotation(
        lambda token: fetch_top_languages(
            username,
            exclude_repo=exclude_repo,
            size_weight=size_weight,
            count_weight=count_weight,
            token=token,
        )
    )

    svg = render_top_languages_card(data, options=params)
    return svg, "top-langs"


def _route_pin(params: dict[str, str]) -> tuple[str, str]:
    username = _validate_username(params.get("username"))

    repo = params.get("repo", "").strip()
    if not repo:
        raise ValueError("Missing required parameter: repo")

    data = retry_with_pat_rotation(
        lambda token: fetch_repo(username, repo, token=token)
    )

    svg = render_repo_card(data, options=params)
    return svg, "pin"


def _route_gist(params: dict[str, str]) -> tuple[str, str]:
    gist_id = params.get("id", "").strip()
    if not gist_id:
        raise ValueError("Missing required parameter: id")

    data = retry_with_pat_rotation(
        lambda token: fetch_gist(gist_id, token=token)
    )

    svg = render_gist_card(data, options=params)
    return svg, "gist"


def _route_wakatime(params: dict[str, str]) -> tuple[str, str]:
    username = params.get("username", "").strip()
    if not username:
        raise ValueError("Missing required parameter: username")

    api_domain = params.get("api_domain", "wakatime.com")

    # WakaTime uses its own auth (API key embedded by the fetcher); no PAT needed.
    data = fetch_wakatime(username, api_domain=api_domain)

    svg = render_wakatime_card(data, options=params)
    return svg, "wakatime"


# ---------------------------------------------------------------------------
# Route table
# ---------------------------------------------------------------------------

# Maps rawPath -> handler callable
_ROUTES: dict[str, Callable[[dict[str, str]], tuple[str, str]]] = {
    "/api": _route_stats,
    "/api/top-langs": _route_top_langs,
    "/api/pin": _route_pin,
    "/api/gist": _route_gist,
    "/api/wakatime": _route_wakatime,
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def route(path: str, params: dict[str, str]) -> tuple[str, str]:
    """Dispatch *path* to its handler, returning (svg, cache_key).

    Args:
        path: The ``rawPath`` value from the Lambda Function URL v2 event.
        params: Decoded query-string dict (str -> str).

    Returns:
        A 2-tuple of (svg_string, cache_key) where cache_key is a key present
        in ``common.cache.CACHE_TTL`` (e.g. "stats", "top-langs", etc.).

    Raises:
        KeyError: Unknown path (caller should convert to 404).
        ValueError: Invalid or disallowed parameter (caller returns error card).
        Any exception from fetchers/renderers propagates to the caller.
    """
    handler = _ROUTES.get(path)
    if handler is None:
        raise KeyError(f"No route for path: {path!r}")
    return handler(params)
