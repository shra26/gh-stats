# fetchers/top_langs_fetcher.py -- Fetch per-language byte stats from owned repos.
# Import as: from fetchers.top_langs_fetcher import fetch_top_languages

from __future__ import annotations

from typing import Any

from common.http_client import graphql


_TOP_LANGS_QUERY = """
query getTopLanguages($login: String!) {
  user(login: $login) {
    repositories(
      ownerAffiliations: OWNER
      isFork: false
      first: 100
    ) {
      nodes {
        name
        languages(
          first: 10
          orderBy: { field: SIZE, direction: DESC }
        ) {
          edges {
            size
            node {
              color
              name
            }
          }
        }
      }
    }
  }
}
"""


def fetch_top_languages(
    username: str,
    *,
    exclude_repo: list[str] | None = None,
    size_weight: float = 1,
    count_weight: float = 0,
    token: str,
) -> dict[str, dict[str, Any]]:
    """Fetch and aggregate language usage across a user's owned, non-forked repos.

    Language entries are ranked by ``size ** size_weight * count ** count_weight``
    (defaults to pure byte-size ranking). The returned dict preserves insertion
    order (descending by computed size), so callers can slice with
    ``itertools.islice`` to respect a ``langs_count`` limit.

    Args:
        username: GitHub login name.
        exclude_repo: Repository names to skip when aggregating.
        size_weight: Exponent applied to the summed byte size when ranking.
        count_weight: Exponent applied to the repo count when ranking.
        token: GitHub PAT.

    Returns:
        Dict keyed by language name; each value is a dict with keys:
        name, color (str or None), size (int, total bytes), count (int, repo count).
        Ordered descending by computed ranking size.
    """
    exclude: set[str] = set(exclude_repo or [])

    body = graphql(_TOP_LANGS_QUERY, {"login": username}, token)
    repos: list[dict[str, Any]] = body["data"]["user"]["repositories"]["nodes"]

    # -- Aggregate across repos -----------------------------------------------
    lang_map: dict[str, dict[str, Any]] = {}

    for repo in repos:
        if repo["name"] in exclude:
            continue
        for edge in repo["languages"]["edges"]:
            lang_node: dict[str, Any] = edge["node"]
            lang_name: str = lang_node["name"]
            byte_size: int = edge["size"]

            if lang_name in lang_map:
                lang_map[lang_name]["size"] += byte_size
                lang_map[lang_name]["count"] += 1
            else:
                lang_map[lang_name] = {
                    "name": lang_name,
                    "color": lang_node.get("color"),
                    "size": byte_size,
                    "count": 1,
                }

    # -- Sort by computed ranking size (descending) ----------------------------
    def _rank_key(entry: dict[str, Any]) -> float:
        s: float = float(entry["size"])
        c: float = float(entry["count"])
        # Guard against zero base with fractional exponent.
        return (s ** size_weight) * (c ** count_weight) if s > 0 else 0.0

    sorted_entries = sorted(lang_map.values(), key=_rank_key, reverse=True)

    return {entry["name"]: entry for entry in sorted_entries}
