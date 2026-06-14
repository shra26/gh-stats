# fetchers/stats_fetcher.py -- Fetch GitHub user stats via GraphQL v4 + optional REST.
# Import as: from fetchers.stats_fetcher import fetch_stats

from __future__ import annotations

from typing import Any

from common.http_client import graphql, rest_get
from config import GITHUB_REST_SEARCH_COMMITS_URL
from rank import calculate_rank


_STATS_QUERY = """
query getUserStats($login: String!) {
  user(login: $login) {
    name
    contributionsCollection {
      totalCommitContributions
      totalPullRequestReviewContributions
    }
    repositoriesContributedTo(first: 1, includeUserRepositories: true) {
      totalCount
    }
    pullRequests(first: 1) {
      totalCount
    }
    mergedPullRequests: pullRequests(states: MERGED, first: 1) {
      totalCount
    }
    openIssues: issues(states: OPEN) {
      totalCount
    }
    closedIssues: issues(states: CLOSED) {
      totalCount
    }
    followers {
      totalCount
    }
    repositoryDiscussions {
      totalCount
    }
    repositoryDiscussionComments(onlyAnswers: true) {
      totalCount
    }
    repositories(
      first: 100
      ownerAffiliations: OWNER
      orderBy: { field: STARGAZERS, direction: DESC }
    ) {
      totalCount
      nodes {
        name
        stargazers {
          totalCount
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""


def fetch_stats(
    username: str,
    *,
    include_all_commits: bool = False,
    exclude_repo: list[str] | None = None,
    token: str,
) -> dict[str, Any]:
    """Fetch GitHub user stats and return a plain dict suitable for rendering.

    Args:
        username: GitHub login name.
        include_all_commits: When True, fetch total commit count via REST search
            (all-time, crosses year boundaries). When False, use contributionsCollection
            (current year only, fast, no extra API call).
        exclude_repo: Repository names (not full names) to exclude from star count.
        token: GitHub PAT with read:user + public_repo scope.

    Returns:
        Dict with keys: name, username, totalStars, totalCommits, totalPRs,
        totalPRsMerged, mergedPRsPercentage, totalReviews, totalIssues,
        totalDiscussionsStarted, totalDiscussionsAnswered, contributedTo,
        followers, rank.
    """
    exclude: set[str] = set(exclude_repo or [])

    body = graphql(_STATS_QUERY, {"login": username}, token)
    user: dict[str, Any] = body["data"]["user"]

    # -- Stars: sum over the first page (up to 100 most-starred owned repos) ----
    total_stars: int = 0
    for repo in user["repositories"]["nodes"]:
        if repo["name"] not in exclude:
            total_stars += repo["stargazers"]["totalCount"]

    # -- Commits ---------------------------------------------------------------
    if include_all_commits:
        search_body = rest_get(
            GITHUB_REST_SEARCH_COMMITS_URL,
            token,
            accept="application/vnd.github.cloak-preview",
            params={"q": f"author:{username}"},
        )
        total_commits: int = search_body["total_count"]
    else:
        total_commits = user["contributionsCollection"]["totalCommitContributions"]

    # -- Derived metrics -------------------------------------------------------
    total_prs: int = user["pullRequests"]["totalCount"]
    total_prs_merged: int = user["mergedPullRequests"]["totalCount"]
    merged_prs_percentage: float = (
        (total_prs_merged / total_prs * 100) if total_prs else 0.0
    )
    total_reviews: int = user["contributionsCollection"][
        "totalPullRequestReviewContributions"
    ]
    open_issues: int = user["openIssues"]["totalCount"]
    closed_issues: int = user["closedIssues"]["totalCount"]
    total_issues: int = open_issues + closed_issues
    total_discussions_started: int = user["repositoryDiscussions"]["totalCount"]
    total_discussions_answered: int = user["repositoryDiscussionComments"]["totalCount"]
    contributed_to: int = user["repositoriesContributedTo"]["totalCount"]
    followers: int = user["followers"]["totalCount"]

    # -- Rank ------------------------------------------------------------------
    rank: dict[str, Any] = calculate_rank(
        all_commits=include_all_commits,
        commits=total_commits,
        prs=total_prs,
        issues=total_issues,
        reviews=total_reviews,
        stars=total_stars,
        followers=followers,
    )

    return {
        "name": user.get("name") or username,
        "username": username,
        "totalStars": total_stars,
        "totalCommits": total_commits,
        "totalPRs": total_prs,
        "totalPRsMerged": total_prs_merged,
        "mergedPRsPercentage": merged_prs_percentage,
        "totalReviews": total_reviews,
        "totalIssues": total_issues,
        "totalDiscussionsStarted": total_discussions_started,
        "totalDiscussionsAnswered": total_discussions_answered,
        "contributedTo": contributed_to,
        "followers": followers,
        "rank": rank,
    }
