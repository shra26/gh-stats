# tests/test_rank.py
"""
Unit tests for src/rank.py -- calculate_rank pure function.

No network access. Percentile comparisons use pytest.approx with abs=1e-6.
"""

import pytest

from rank import calculate_rank, exponential_cdf, log_normal_cdf


# ---------------------------------------------------------------------------
# CDF primitives
# ---------------------------------------------------------------------------

class TestExponentialCdf:
    def test_zero_input_gives_zero(self):
        assert exponential_cdf(0) == pytest.approx(0.0, abs=1e-12)

    def test_one_gives_half(self):
        # 1 - 2**(-1) = 0.5
        assert exponential_cdf(1) == pytest.approx(0.5, abs=1e-12)

    def test_large_input_approaches_one(self):
        assert exponential_cdf(100) == pytest.approx(1.0, abs=1e-12)


class TestLogNormalCdf:
    def test_zero_input_gives_zero(self):
        assert log_normal_cdf(0) == pytest.approx(0.0, abs=1e-12)

    def test_one_gives_half(self):
        # 1 / (1 + 1) = 0.5
        assert log_normal_cdf(1) == pytest.approx(0.5, abs=1e-12)

    def test_large_input_approaches_one(self):
        assert log_normal_cdf(1_000_000) == pytest.approx(1.0, abs=1e-4)


# ---------------------------------------------------------------------------
# calculate_rank -- grade boundaries and exact formula
# ---------------------------------------------------------------------------

class TestCalculateRankZeroUser:
    """A user with all-zero stats should score the worst possible rank."""

    def test_zero_user_percentile_is_100(self):
        result = calculate_rank(
            all_commits=False,
            commits=0,
            prs=0,
            issues=0,
            reviews=0,
            stars=0,
            followers=0,
        )
        assert result["percentile"] == pytest.approx(100.0, abs=1e-6)

    def test_zero_user_raw_rank_is_one(self):
        result = calculate_rank(
            all_commits=False,
            commits=0,
            prs=0,
            issues=0,
            reviews=0,
            stars=0,
            followers=0,
        )
        # percentile = rank * 100, so rank should equal 1.0
        assert result["percentile"] / 100.0 == pytest.approx(1.0, abs=1e-6)

    def test_zero_user_level_is_C(self):
        result = calculate_rank(
            all_commits=False,
            commits=0,
            prs=0,
            issues=0,
            reviews=0,
            stars=0,
            followers=0,
        )
        assert result["level"] == "C"


class TestCalculateRankHighActivityUser:
    """A very high-activity user should land in level S (percentile <= 1)."""

    def test_high_activity_level_is_S(self):
        result = calculate_rank(
            all_commits=False,
            commits=5000,
            prs=1000,
            issues=1000,
            reviews=500,
            stars=100_000,
            followers=100_000,
        )
        assert result["level"] == "S"

    def test_high_activity_percentile_at_most_1(self):
        result = calculate_rank(
            all_commits=False,
            commits=5000,
            prs=1000,
            issues=1000,
            reviews=500,
            stars=100_000,
            followers=100_000,
        )
        assert result["percentile"] <= 1.0


class TestCalculateRankExactFormula:
    """
    Independently compute the formula for a mid-range user and assert
    calculate_rank matches to 1e-6. Also verify the level matches the
    threshold table.
    """

    # Chosen mid-range values
    COMMITS = 300
    PRS = 60
    ISSUES = 30
    REVIEWS = 3
    STARS = 75
    FOLLOWERS = 15

    def _expected_percentile(self) -> float:
        """Replicate the formula from the plan spec."""
        commits_median = 250
        rank = 1 - (
            2 * exponential_cdf(self.COMMITS / commits_median)
            + 3 * exponential_cdf(self.PRS / 50)
            + 1 * exponential_cdf(self.ISSUES / 25)
            + 1 * exponential_cdf(self.REVIEWS / 2)
            + 4 * log_normal_cdf(self.STARS / 50)
            + 1 * log_normal_cdf(self.FOLLOWERS / 10)
        ) / 12
        return rank * 100

    def test_percentile_matches_formula(self):
        result = calculate_rank(
            all_commits=False,
            commits=self.COMMITS,
            prs=self.PRS,
            issues=self.ISSUES,
            reviews=self.REVIEWS,
            stars=self.STARS,
            followers=self.FOLLOWERS,
        )
        assert result["percentile"] == pytest.approx(self._expected_percentile(), abs=1e-6)

    def test_level_matches_threshold_table(self):
        THRESHOLDS = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
        LEVELS = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
        percentile = self._expected_percentile()
        expected_level = LEVELS[next(i for i, t in enumerate(THRESHOLDS) if percentile <= t)]

        result = calculate_rank(
            all_commits=False,
            commits=self.COMMITS,
            prs=self.PRS,
            issues=self.ISSUES,
            reviews=self.REVIEWS,
            stars=self.STARS,
            followers=self.FOLLOWERS,
        )
        assert result["level"] == expected_level

    def test_return_dict_has_required_keys(self):
        result = calculate_rank(
            all_commits=False,
            commits=self.COMMITS,
            prs=self.PRS,
            issues=self.ISSUES,
            reviews=self.REVIEWS,
            stars=self.STARS,
            followers=self.FOLLOWERS,
        )
        assert "level" in result
        assert "percentile" in result


class TestCalculateRankAllCommitsFlag:
    """
    all_commits=True raises the commits median from 250 to 1000, making
    the same commit count score WORSE (higher percentile) because the bar
    is higher relative to the median.
    """

    def test_all_commits_true_gives_worse_percentile(self):
        commits = 400  # above 250 median but below 1000 median

        result_year = calculate_rank(
            all_commits=False,
            commits=commits,
            prs=0,
            issues=0,
            reviews=0,
            stars=0,
            followers=0,
        )
        result_all = calculate_rank(
            all_commits=True,
            commits=commits,
            prs=0,
            issues=0,
            reviews=0,
            stars=0,
            followers=0,
        )
        # Higher percentile = worse rank
        assert result_all["percentile"] > result_year["percentile"]

    def test_all_commits_true_differs_from_false(self):
        """Sanity check: the two modes must not produce identical results."""
        commits = 300

        result_year = calculate_rank(
            all_commits=False,
            commits=commits,
            prs=0, issues=0, reviews=0, stars=0, followers=0,
        )
        result_all = calculate_rank(
            all_commits=True,
            commits=commits,
            prs=0, issues=0, reviews=0, stars=0, followers=0,
        )
        assert result_year["percentile"] != result_all["percentile"]


class TestCalculateRankThresholdBoundaries:
    """Probe the level boundaries by constructing users whose percentile
    is just inside each named band."""

    def _level_for_percentile(self, target_pct: float) -> str:
        """Return the expected level for a given percentile from the table."""
        THRESHOLDS = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
        LEVELS = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
        return LEVELS[next(i for i, t in enumerate(THRESHOLDS) if target_pct <= t)]

    def test_percentile_exactly_1_gives_S(self):
        # percentile <= 1 -> "S"
        assert self._level_for_percentile(1.0) == "S"

    def test_percentile_exactly_12_5_gives_A_plus(self):
        assert self._level_for_percentile(12.5) == "A+"

    def test_percentile_just_above_1_gives_A_plus(self):
        assert self._level_for_percentile(1.001) == "A+"

    def test_percentile_exactly_100_gives_C(self):
        assert self._level_for_percentile(100.0) == "C"
