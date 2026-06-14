"""
Rank calculation for gh-stats.

Implements the exact algorithm from the original github-readme-stats.
Base-2 exponential CDF is intentional (not natural log base e).
Lower percentile = better rank.
"""


def exponential_cdf(x: float) -> float:
    """CDF approximation used for commits, PRs, issues, and reviews."""
    return 1 - 2 ** (-x)


def log_normal_cdf(x: float) -> float:
    """CDF approximation used for stars and followers."""
    return x / (1 + x)


def calculate_rank(
    *,
    all_commits: bool,
    commits: int,
    prs: int,
    issues: int,
    reviews: int,
    stars: int,
    followers: int,
) -> dict[str, object]:
    """
    Compute rank level and percentile from GitHub stats.

    Parameters
    ----------
    all_commits:
        When True, the commits median is raised to 1000 (include_all_commits
        mode), reflecting a career total rather than a single year.
    commits:
        Total commit count (year-scoped or all-time, matching all_commits).
    prs:
        Total pull requests opened.
    issues:
        Total issues opened.
    reviews:
        Total pull request reviews.
    stars:
        Total stargazers across owned repositories.
    followers:
        Total GitHub followers.

    Returns
    -------
    dict with keys:
        level      - one of S, A+, A, A-, B+, B, B-, C+, C
        percentile - float in [0, 100], lower is better
    """
    COMMITS_MEDIAN = 1000 if all_commits else 250
    COMMITS_WEIGHT = 2

    PRS_MEDIAN = 50
    PRS_WEIGHT = 3

    ISSUES_MEDIAN = 25
    ISSUES_WEIGHT = 1

    REVIEWS_MEDIAN = 2
    REVIEWS_WEIGHT = 1

    STARS_MEDIAN = 50
    STARS_WEIGHT = 4

    FOLLOWERS_MEDIAN = 10
    FOLLOWERS_WEIGHT = 1

    TOTAL_WEIGHT = 12

    rank = 1 - (
        COMMITS_WEIGHT * exponential_cdf(commits / COMMITS_MEDIAN)
        + PRS_WEIGHT * exponential_cdf(prs / PRS_MEDIAN)
        + ISSUES_WEIGHT * exponential_cdf(issues / ISSUES_MEDIAN)
        + REVIEWS_WEIGHT * exponential_cdf(reviews / REVIEWS_MEDIAN)
        + STARS_WEIGHT * log_normal_cdf(stars / STARS_MEDIAN)
        + FOLLOWERS_WEIGHT * log_normal_cdf(followers / FOLLOWERS_MEDIAN)
    ) / TOTAL_WEIGHT

    percentile = rank * 100

    THRESHOLDS = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    LEVELS = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]

    level = LEVELS[next(i for i, t in enumerate(THRESHOLDS) if percentile <= t)]

    return {"level": level, "percentile": percentile}
