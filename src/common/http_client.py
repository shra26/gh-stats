# common/http_client.py -- urllib3-backed GitHub API client (GraphQL + REST GET).
# One module-global PoolManager is reused across warm Lambda invocations.
# Import as: from common.http_client import graphql, rest_get, RateLimitError, ...

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any

import urllib3

from config import GITHUB_GRAPHQL_URL


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class GitHubError(Exception):
    """Base class for all GitHub API errors raised by this module."""


class RateLimitError(GitHubError):
    """Raised when the GitHub API signals a rate-limit condition."""


class BadCredentialsError(GitHubError):
    """Raised when the PAT is invalid or expired."""


class AccountSuspendedError(GitHubError):
    """Raised when the authenticated account has been suspended."""


class GraphQLError(GitHubError):
    """Raised for GraphQL-level errors that are not rate-limit or auth errors.

    The raw error payload is stored in ``errors``.
    """

    def __init__(self, message: str, errors: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.errors = errors


class NoTokensError(GitHubError):
    """Raised when the PAT list is empty and no token is available."""


class MaxRetriesError(GitHubError):
    """Raised when all PATs have been exhausted due to rate-limit or auth errors."""


# ---------------------------------------------------------------------------
# Module-global connection pool
# ---------------------------------------------------------------------------

_POOL: urllib3.PoolManager = urllib3.PoolManager(
    num_pools=4,
    maxsize=4,
    headers={
        "User-Agent": "gh-stats",
        "Content-Type": "application/json",
    },
)

# Pattern that indicates a rate-limit message from GitHub (REST or GraphQL).
_RATE_LIMIT_RE: re.Pattern[str] = re.compile(
    r"rate.?limit|api rate|exceeded.*rate|secondary rate",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _classify_graphql_errors(errors: list[dict[str, Any]]) -> GitHubError:
    """Map a GraphQL ``errors`` list to the most specific exception subclass."""
    for err in errors:
        err_type: str = err.get("type", "")
        message: str = err.get("message", "")

        if err_type == "RATE_LIMITED" or _RATE_LIMIT_RE.search(message):
            return RateLimitError(message or "GitHub rate limit exceeded")

        if "bad credentials" in message.lower():
            return BadCredentialsError(message)

        if "account suspended" in message.lower():
            return AccountSuspendedError(message)

    # Generic GraphQL error -- surface the full payload.
    first_msg: str = errors[0].get("message", "GraphQL error") if errors else "GraphQL error"
    return GraphQLError(first_msg, errors)


def _classify_http_error(status: int, body: bytes) -> GitHubError | None:
    """Return an exception for 401/403/429 HTTP responses, or None for success."""
    if status == 200:
        return None

    try:
        payload: dict[str, Any] = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        payload = {}

    message: str = payload.get("message", "")

    if status == 429 or _RATE_LIMIT_RE.search(message):
        return RateLimitError(message or f"HTTP {status} rate limit")

    if status in (401, 403):
        if "bad credentials" in message.lower():
            return BadCredentialsError(message)
        if "account suspended" in message.lower():
            return AccountSuspendedError(message)
        return BadCredentialsError(message or f"HTTP {status} auth error")

    return GitHubError(f"HTTP {status}: {message or body[:200]!r}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def graphql(query: str, variables: dict[str, Any], token: str) -> dict[str, Any]:
    """POST a GraphQL query to the GitHub v4 API and return the parsed response body.

    The caller receives the *entire* parsed JSON dict (including ``"data"`` and
    any ``"errors"`` keys).  If the response contains top-level ``"errors"``,
    an appropriate exception is raised before returning.

    Raises:
        RateLimitError: GitHub RATE_LIMITED type or rate-limit message.
        BadCredentialsError: Invalid or expired PAT.
        AccountSuspendedError: Authenticated account suspended.
        GraphQLError: Any other GraphQL-level error.
        GitHubError: Non-200 HTTP response not covered above.
    """
    payload: bytes = json.dumps({"query": query, "variables": variables}).encode()
    headers: dict[str, str] = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "gh-stats",
    }

    response: urllib3.BaseHTTPResponse = _POOL.request(
        "POST",
        GITHUB_GRAPHQL_URL,
        body=payload,
        headers=headers,
    )

    http_error = _classify_http_error(response.status, response.data)
    if http_error is not None:
        raise http_error

    body_parsed: dict[str, Any] = json.loads(response.data)

    errors = body_parsed.get("errors")
    if errors:
        raise _classify_graphql_errors(errors)

    return body_parsed


def rest_get(
    url: str,
    token: str,
    accept: str | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform an authenticated GET against a GitHub REST endpoint.

    Args:
        url: Full URL (e.g. GITHUB_REST_SEARCH_COMMITS_URL).
        token: GitHub PAT; sent as ``Authorization: token <token>``.
        accept: Optional ``Accept`` header value (e.g.
            ``"application/vnd.github.cloak-preview"``).
        params: Optional query-string parameters; URL-encoded and appended.

    Returns:
        Parsed JSON response body.

    Raises:
        RateLimitError, BadCredentialsError, AccountSuspendedError, GitHubError.
    """
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    headers: dict[str, str] = {
        "Authorization": f"token {token}",
        "User-Agent": "gh-stats",
    }
    if accept is not None:
        headers["Accept"] = accept

    response: urllib3.BaseHTTPResponse = _POOL.request(
        "GET",
        url,
        headers=headers,
    )

    http_error = _classify_http_error(response.status, response.data)
    if http_error is not None:
        raise http_error

    return json.loads(response.data)  # type: ignore[return-value]
