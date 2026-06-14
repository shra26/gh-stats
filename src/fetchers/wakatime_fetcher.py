# fetchers/wakatime_fetcher.py -- Fetch public WakaTime coding stats for a user.
# Import as: from fetchers.wakatime_fetcher import fetch_wakatime

from __future__ import annotations

from typing import Any

from common.http_client import rest_get


def fetch_wakatime(
    username: str,
    *,
    api_domain: str = "wakatime.com",
) -> dict[str, Any]:
    """Fetch public WakaTime coding stats for a user.

    Calls the WakaTime public stats endpoint. The user must have enabled
    public statistics in their WakaTime profile settings.

    Args:
        username: WakaTime username (not GitHub username).
        api_domain: WakaTime API domain. Override for self-hosted Wakapi
            instances (e.g. "wakapi.example.com").

    Returns:
        The ``data`` object from the WakaTime API response, which contains
        keys such as: languages (list), total_seconds, human_readable_total,
        daily_average, best_day, editors, operating_systems, etc.

    Raises:
        GitHubError: Propagated from rest_get on non-200 HTTP responses.
            (WakaTime uses the same HTTP error shape for rate limits / auth.)
    """
    url = f"https://{api_domain}/api/v1/users/{username}/stats"
    response: dict[str, Any] = rest_get(
        url,
        token="",
        params={"is_including_today": "true"},
    )
    return response["data"]
