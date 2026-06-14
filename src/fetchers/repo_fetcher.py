# fetchers/repo_fetcher.py -- Fetch a single GitHub repository (user or org).
# Import as: from fetchers.repo_fetcher import fetch_repo

from __future__ import annotations

from typing import Any

from common.http_client import graphql, GraphQLError


_REPO_QUERY = """
query getRepo($login: String!, $repo: String!) {
  user(login: $login) {
    repository(name: $repo) {
      ...RepoInfo
    }
  }
  organization(login: $login) {
    repository(name: $repo) {
      ...RepoInfo
    }
  }
}

fragment RepoInfo on Repository {
  name
  nameWithOwner
  isPrivate
  isArchived
  isTemplate
  stargazers {
    totalCount
  }
  description
  primaryLanguage {
    color
    id
    name
  }
  forkCount
}
"""


def fetch_repo(username: str, reponame: str, *, token: str) -> dict[str, Any]:
    """Fetch metadata for a single public repository owned by a user or org.

    Queries both the ``user`` and ``organization`` root fields and picks
    whichever returns a non-null repository. Private repos are rejected.

    Args:
        username: GitHub login (user or org name).
        reponame: Repository name (without owner prefix).
        token: GitHub PAT.

    Returns:
        Dict with keys: name, nameWithOwner, description, primaryLanguage
        (dict with color/id/name, or None), starCount, forkCount,
        isArchived, isTemplate.

    Raises:
        GraphQLError: If both user.repository and organization.repository are null,
            or if the repo is private.
    """
    body = graphql(_REPO_QUERY, {"login": username, "repo": reponame}, token)
    data: dict[str, Any] = body["data"]

    user_node: dict[str, Any] | None = (data.get("user") or {}).get("repository")
    org_node: dict[str, Any] | None = (data.get("organization") or {}).get("repository")

    repo: dict[str, Any] | None = user_node or org_node

    if repo is None:
        raise GraphQLError(
            f"Repository '{username}/{reponame}' not found",
            [],
        )

    if repo.get("isPrivate"):
        raise GraphQLError(
            f"Repository '{username}/{reponame}' is private",
            [],
        )

    primary_lang = repo.get("primaryLanguage")

    return {
        "name": repo["name"],
        "nameWithOwner": repo["nameWithOwner"],
        "description": repo.get("description"),
        "primaryLanguage": primary_lang,
        "starCount": repo["stargazers"]["totalCount"],
        "forkCount": repo["forkCount"],
        "isArchived": repo.get("isArchived", False),
        "isTemplate": repo.get("isTemplate", False),
    }
