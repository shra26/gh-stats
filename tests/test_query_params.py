# tests/test_query_params.py
"""
Unit tests for src/common/query_params.py.

Covers: parse_bool, parse_array, parse_int, is_valid_username, is_whitelisted.
Uses monkeypatch to test WHITELIST behaviour without reading real env vars.
No network access.
"""

import pytest

from common import query_params as qp
from common.query_params import (
    parse_bool,
    parse_array,
    parse_int,
    is_valid_username,
    is_whitelisted,
)


# ---------------------------------------------------------------------------
# parse_bool
# ---------------------------------------------------------------------------

class TestParseBool:
    def test_true_lowercase(self):
        assert parse_bool("true") is True

    def test_false_lowercase(self):
        assert parse_bool("false") is False

    def test_true_uppercase(self):
        assert parse_bool("TRUE") is True

    def test_false_uppercase(self):
        assert parse_bool("FALSE") is False

    def test_true_mixed_case(self):
        assert parse_bool("True") is True

    def test_none_returns_default_false(self):
        assert parse_bool(None) is False

    def test_none_with_explicit_true_default(self):
        assert parse_bool(None, default=True) is True

    def test_none_with_explicit_false_default(self):
        assert parse_bool(None, default=False) is False

    def test_unrecognised_value_returns_default(self):
        assert parse_bool("yes") is False

    def test_unrecognised_value_with_true_default(self):
        assert parse_bool("1", default=True) is True

    def test_empty_string_returns_default(self):
        assert parse_bool("") is False

    def test_whitespace_value_returns_default(self):
        assert parse_bool("   ") is False

    def test_true_with_surrounding_whitespace(self):
        assert parse_bool("  true  ") is True


# ---------------------------------------------------------------------------
# parse_array
# ---------------------------------------------------------------------------

class TestParseArray:
    def test_comma_separated_values(self):
        assert parse_array("stars,commits,prs") == ["stars", "commits", "prs"]

    def test_none_returns_empty_list(self):
        assert parse_array(None) == []

    def test_empty_string_returns_empty_list(self):
        assert parse_array("") == []

    def test_single_value(self):
        assert parse_array("stars") == ["stars"]

    def test_strips_whitespace_around_items(self):
        result = parse_array("stars, commits , prs")
        assert result == ["stars", "commits", "prs"]

    def test_drops_empty_tokens(self):
        # Leading/trailing commas produce empty tokens that must be dropped
        result = parse_array(",stars,,commits,")
        assert result == ["stars", "commits"]

    def test_whitespace_only_string_returns_empty(self):
        assert parse_array("   ") == []


# ---------------------------------------------------------------------------
# parse_int
# ---------------------------------------------------------------------------

class TestParseInt:
    def test_valid_integer_string(self):
        assert parse_int("7", 0) == 7

    def test_none_returns_default(self):
        assert parse_int(None, 5) == 5

    def test_non_numeric_returns_default(self):
        assert parse_int("x", 3) == 3

    def test_float_string_returns_default(self):
        # int("3.5") raises ValueError; should fall back
        assert parse_int("3.5", 0) == 0

    def test_zero_string(self):
        assert parse_int("0", 99) == 0

    def test_negative_string(self):
        assert parse_int("-5", 0) == -5

    def test_value_with_whitespace(self):
        assert parse_int("  10  ", 0) == 10

    def test_empty_string_returns_default(self):
        assert parse_int("", 42) == 42


# ---------------------------------------------------------------------------
# is_valid_username
# ---------------------------------------------------------------------------

class TestIsValidUsername:
    def test_known_valid_username(self):
        assert is_valid_username("anuraghazra") is True

    def test_single_letter(self):
        assert is_valid_username("a") is True

    def test_alphanumeric_with_hyphen(self):
        assert is_valid_username("john-doe") is True

    def test_none_returns_false(self):
        assert is_valid_username(None) is False

    def test_empty_string_returns_false(self):
        assert is_valid_username("") is False

    def test_starts_with_hyphen_returns_false(self):
        assert is_valid_username("-bad") is False

    def test_ends_with_hyphen_returns_false(self):
        assert is_valid_username("bad-") is False

    def test_consecutive_hyphens_returns_false(self):
        # GitHub does not allow two consecutive hyphens
        assert is_valid_username("a--b") is False

    def test_40_char_username_returns_false(self):
        # Max is 39 characters
        assert is_valid_username("a" * 40) is False

    def test_39_char_username_returns_true(self):
        assert is_valid_username("a" * 39) is True

    def test_special_chars_returns_false(self):
        assert is_valid_username("user@name") is False

    def test_underscore_returns_false(self):
        # GitHub usernames do not allow underscores
        assert is_valid_username("user_name") is False


# ---------------------------------------------------------------------------
# is_whitelisted
# ---------------------------------------------------------------------------

class TestIsWhitelistedOpenMode:
    """When WHITELIST is None (env var unset), all requests pass (allow-all development mode).
    The None check is short-circuited before username validation; even None/empty usernames
    return True because the function is a pure access-control gate in this mode.
    """

    def test_any_user_allowed_when_whitelist_is_none(self, monkeypatch):
        monkeypatch.setattr(qp, "WHITELIST", None)
        assert is_whitelisted("anyone") is True

    def test_known_user_allowed_when_whitelist_is_none(self, monkeypatch):
        monkeypatch.setattr(qp, "WHITELIST", None)
        assert is_whitelisted("anuraghazra") is True

    def test_open_mode_does_not_block_any_string(self, monkeypatch):
        # WHITELIST=None means "allow all" -- even a random string passes
        monkeypatch.setattr(qp, "WHITELIST", None)
        assert is_whitelisted("some-random-user") is True


class TestIsWhitelistedRestrictedMode:
    """When WHITELIST is a list, only listed usernames (case-insensitive) pass."""

    @pytest.fixture(autouse=True)
    def set_whitelist(self, monkeypatch):
        monkeypatch.setattr(qp, "WHITELIST", ["alice"])

    def test_listed_user_is_allowed(self):
        assert is_whitelisted("alice") is True

    def test_unlisted_user_is_blocked(self):
        assert is_whitelisted("bob") is False

    def test_case_insensitive_upper(self):
        assert is_whitelisted("ALICE") is True

    def test_case_insensitive_mixed(self):
        assert is_whitelisted("Alice") is True

    def test_none_username_is_blocked(self):
        assert is_whitelisted(None) is False

    def test_empty_username_is_blocked(self):
        assert is_whitelisted("") is False

    def test_partial_match_is_not_allowed(self):
        assert is_whitelisted("alic") is False

    def test_second_listed_user_allowed(self, monkeypatch):
        monkeypatch.setattr(qp, "WHITELIST", ["alice", "bob"])
        assert is_whitelisted("bob") is True
