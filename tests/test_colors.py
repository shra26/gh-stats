# tests/test_colors.py
"""
Unit tests for src/common/colors.py.

Covers: is_valid_hex_color, fallback_color, get_card_colors.
No network access.
"""

import pytest

from common.colors import is_valid_hex_color, fallback_color, get_card_colors


# ---------------------------------------------------------------------------
# is_valid_hex_color
# ---------------------------------------------------------------------------

class TestIsValidHexColor:
    """Accepted lengths: 3, 4, 6, 8 hex digits -- no leading '#'."""

    def test_accepts_3_digit_hex(self):
        assert is_valid_hex_color("fff") is True

    def test_accepts_3_digit_hex_mixed_case(self):
        assert is_valid_hex_color("ABC") is True

    def test_accepts_4_digit_hex(self):
        assert is_valid_hex_color("ffff") is True

    def test_accepts_6_digit_hex(self):
        assert is_valid_hex_color("ffffff") is True

    def test_accepts_6_digit_hex_numeric(self):
        assert is_valid_hex_color("2f80ed") is True

    def test_accepts_8_digit_hex_with_alpha(self):
        assert is_valid_hex_color("ffffff00") is True

    def test_rejects_hash_prefixed_3_digit(self):
        assert is_valid_hex_color("#fff") is False

    def test_rejects_hash_prefixed_6_digit(self):
        assert is_valid_hex_color("#2f80ed") is False

    def test_rejects_non_hex_chars(self):
        assert is_valid_hex_color("gggggg") is False

    def test_rejects_5_digit_string(self):
        assert is_valid_hex_color("12345") is False

    def test_rejects_empty_string(self):
        assert is_valid_hex_color("") is False

    def test_rejects_non_string(self):
        assert is_valid_hex_color(None) is False  # type: ignore[arg-type]

    def test_rejects_integer(self):
        assert is_valid_hex_color(123) is False  # type: ignore[arg-type]

    def test_accepts_all_lowercase_hex_digits(self):
        assert is_valid_hex_color("abcdef") is True

    def test_accepts_all_uppercase_hex_digits(self):
        assert is_valid_hex_color("ABCDEF") is True


# ---------------------------------------------------------------------------
# fallback_color
# ---------------------------------------------------------------------------

class TestFallbackColor:
    """fallback_color(color, fallback) -> resolved color string or gradient list."""

    def test_valid_hex_prepends_hash(self):
        assert fallback_color("2f80ed", "#000") == "#2f80ed"

    def test_bad_hex_returns_fallback(self):
        assert fallback_color("badhex", "#000") == "#000"

    def test_none_returns_fallback(self):
        assert fallback_color(None, "#000") == "#000"

    def test_hash_prefixed_hex_is_invalid_without_hash(self):
        # "#fff" contains '#' which is not a hex char; fallback is expected
        assert fallback_color("#fff", "#fallback") == "#fallback"

    def test_gradient_three_parts_returns_list(self):
        result = fallback_color("45,1a1b27,2d2d44", "#000")
        assert result == ["45", "1a1b27", "2d2d44"]

    def test_gradient_four_parts_returns_list(self):
        result = fallback_color("90,fff,000,abc", "#000")
        assert isinstance(result, list)
        assert len(result) == 4

    def test_two_comma_parts_is_not_a_gradient(self):
        # Only 2 parts -- not a valid gradient (need angle + at least 2 colors)
        result = fallback_color("45,1a1b27", "#000")
        assert result == "#000"

    def test_gradient_with_bad_color_part_returns_fallback(self):
        # angle is not validated but the color parts must be valid hex
        result = fallback_color("45,zzzzzz,2d2d44", "#000")
        assert result == "#000"

    def test_3_digit_hex_returns_hash_prefixed(self):
        assert fallback_color("fff", "#000") == "#fff"

    def test_8_digit_hex_alpha_returns_hash_prefixed(self):
        assert fallback_color("ffffff00", "#000") == "#ffffff00"


# ---------------------------------------------------------------------------
# get_card_colors
# ---------------------------------------------------------------------------

class TestGetCardColorsDefault:
    """Default theme (no overrides) should return the default palette."""

    def setup_method(self):
        self.colors = get_card_colors(theme="default")

    def test_title_color(self):
        assert self.colors["titleColor"] == "#2f80ed"

    def test_icon_color(self):
        assert self.colors["iconColor"] == "#4c71f2"

    def test_text_color(self):
        assert self.colors["textColor"] == "#434d58"

    def test_bg_color(self):
        assert self.colors["bgColor"] == "#fffefe"

    def test_border_color(self):
        assert self.colors["borderColor"] == "#e4e2e2"

    def test_ring_color_falls_back_to_title_color(self):
        # No ring_color in default theme; should equal resolved titleColor
        assert self.colors["ringColor"] == self.colors["titleColor"]


class TestGetCardColorsThemeOverrideByUserParam:
    """User query param must beat the selected theme."""

    def test_user_title_color_overrides_dark_theme(self):
        colors = get_card_colors(title_color="ff0000", theme="dark")
        assert colors["titleColor"] == "#ff0000"

    def test_dark_theme_non_overridden_key_from_theme(self):
        # dark theme icon_color is 79ff97; we do not override it
        colors = get_card_colors(theme="dark")
        assert colors["iconColor"] == "#79ff97"


class TestGetCardColorsGradientBackground:
    """bg_color may be a gradient string; get_card_colors should return a list."""

    def test_gradient_bg_color_returns_list(self):
        colors = get_card_colors(bg_color="45,1a1b27,2d2d44")
        assert isinstance(colors["bgColor"], list)
        assert colors["bgColor"] == ["45", "1a1b27", "2d2d44"]

    def test_non_gradient_bg_color_returns_string(self):
        colors = get_card_colors(bg_color="151515")
        assert colors["bgColor"] == "#151515"


class TestGetCardColorsRingFallback:
    """ring_color falls back to resolved titleColor when not provided."""

    def test_ring_color_equals_title_when_not_specified(self):
        colors = get_card_colors(title_color="ff0000")
        assert colors["ringColor"] == "#ff0000"

    def test_explicit_ring_color_overrides_title(self):
        colors = get_card_colors(title_color="ff0000", ring_color="00ff00")
        assert colors["ringColor"] == "#00ff00"
        assert colors["titleColor"] == "#ff0000"


class TestGetCardColorsNoTheme:
    """Calling without any theme param should fall back to the default theme."""

    def test_no_theme_uses_default(self):
        colors_no_theme = get_card_colors()
        colors_default = get_card_colors(theme="default")
        assert colors_no_theme == colors_default


class TestGetCardColorsReturnShape:
    """Return dict must have exactly the expected camelCase keys."""

    def test_all_required_keys_present(self):
        colors = get_card_colors()
        required = {"titleColor", "textColor", "iconColor", "bgColor", "borderColor", "ringColor"}
        assert required.issubset(colors.keys())
