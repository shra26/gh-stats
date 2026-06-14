# fetchers/gist_fetcher.py -- Fetch a GitHub Gist by name via GraphQL viewer scope.
# Import as: from fetchers.gist_fetcher import fetch_gist

from __future__ import annotations

from typing import Any

from common.http_client import graphql, GraphQLError


_GIST_QUERY = """
query getGist($gistName: String!) {
  viewer {
    gist(name: $gistName) {
      description
      owner {
        login
      }
      stargazerCount
      forks {
        totalCount
      }
      files {
        name
        language {
          name
        }
        size
      }
    }
  }
}
"""


def fetch_gist(gist_id: str, *, token: str) -> dict[str, Any]:
    """Fetch metadata for a single public GitHub Gist.

    Uses the ``viewer.gist(name:)`` GraphQL field, which requires the PAT
    owner to have access to the gist. Returns the first (or largest) file
    as the representative file for the card.

    Args:
        gist_id: The gist short-name / hash identifier (not the full URL).
        token: GitHub PAT.

    Returns:
        Dict with keys: name (first file name), nameWithOwner, description,
        language (primary file language name, or None), starsCount,
        forksCount, ownerLogin.

    Raises:
        GraphQLError: If the gist is not found or has no files.
    """
    body = graphql(_GIST_QUERY, {"gistName": gist_id}, token)
    gist: dict[str, Any] | None = body["data"]["viewer"].get("gist")

    if gist is None:
        raise GraphQLError(f"Gist '{gist_id}' not found", [])

    files: list[dict[str, Any]] = gist.get("files") or []

    if not files:
        raise GraphQLError(f"Gist '{gist_id}' has no files", [])

    # Pick the largest file by byte size as the primary/representative file.
    # Fall back to the first file if sizes are absent (size can be None for binary).
    def _file_size(f: dict[str, Any]) -> int:
        return f.get("size") or 0

    primary_file: dict[str, Any] = max(files, key=_file_size)

    owner_login: str = (gist.get("owner") or {}).get("login", "")
    file_name: str = primary_file.get("name") or gist_id

    lang_node = primary_file.get("language")
    language: str | None = lang_node.get("name") if lang_node else None

    return {
        "name": file_name,
        "nameWithOwner": f"{owner_login}/{file_name}" if owner_login else file_name,
        "description": gist.get("description"),
        "language": language,
        "starsCount": gist.get("stargazerCount", 0),
        "forksCount": (gist.get("forks") or {}).get("totalCount", 0),
        "ownerLogin": owner_login,
    }
