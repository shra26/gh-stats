# tests/test_render_utils.py
"""
Unit tests for src/common/render_utils.py.

Covers: k_formatter, format_number, clamp, encode_html.
No network access.
"""

import pytest

from common.render_utils import k_formatter, format_number, clamp, encode_html


# ---------------------------------------------------------------------------
# k_formatter
# ---------------------------------------------------------------------------

class TestKFormatter:
    """Exact string output matches the github-readme-stats JS kFormatter."""

    # Below 1 000 -- plain integer strings
    def test_zero(self):
        assert k_formatter(0) == "0"

    def test_positive_below_1k(self):
        assert k_formatter(999) == "999"

    def test_one(self):
        assert k_formatter(1) == "1"

    # Boundary: 1 000
    def test_exactly_1000(self):
        assert k_formatter(1000) == "1k"

    # Midpoints
    def test_1500_gives_1_5k(self):
        result = k_formatter(1500)
        # Exact or at minimum starts with "1.5"
        assert result.startswith("1.5") and result.endswith("k")

    def test_1100(self):
        assert k_formatter(1100) == "1.1k"

    def test_9999(self):
        assert k_formatter(9999) == "10k"  # rounds 9.999 -> 10.0 -> trailing .0 stripped

    def test_exactly_1_million(self):
        assert k_formatter(1_000_000) == "1m"

    def test_1_5_million(self):
        result = k_formatter(1_500_000)
        assert result.startswith("1.5") and result.endswith("m")

    def test_2_million(self):
        assert k_formatter(2_000_000) == "2m"

    # Float input
    def test_float_below_1k(self):
        assert k_formatter(42.9) == "43"

    def test_float_above_1k(self):
        assert k_formatter(1234.5) == "1.2k"

    def test_trailing_zero_stripped_for_round_thousands(self):
        # 5000 -> "5k" not "5.0k"
        assert k_formatter(5000) == "5k"


# ---------------------------------------------------------------------------
# format_number
# ---------------------------------------------------------------------------

class TestFormatNumber:
    """format_number delegates short/long display modes."""

    def test_short_below_1k(self):
        assert format_number(500) == "500"

    def test_short_exactly_1k(self):
        assert format_number(1000) == "1k"

    def test_short_1500(self):
        result = format_number(1500)
        assert result.startswith("1.5") and result.endswith("k")

    def test_long_no_suffix(self):
        assert format_number(1500, number_format="long") == "1,500"

    def test_long_million(self):
        assert format_number(1_000_000, number_format="long") == "1,000,000"

    def test_long_small_number(self):
        assert format_number(42, number_format="long") == "42"


# ---------------------------------------------------------------------------
# clamp
# ---------------------------------------------------------------------------

class TestClamp:
    """clamp(value, lo, hi) returns value pinned to [lo, hi]."""

    def test_within_range(self):
        assert clamp(5, 0, 10) == 5

    def test_below_lo(self):
        assert clamp(-1, 0, 10) == 0

    def test_above_hi(self):
        assert clamp(20, 0, 10) == 10

    def test_equal_to_lo(self):
        assert clamp(0, 0, 10) == 0

    def test_equal_to_hi(self):
        assert clamp(10, 0, 10) == 10

    def test_float_within_range(self):
        assert clamp(3.5, 0.0, 5.0) == pytest.approx(3.5)

    def test_float_below_lo(self):
        assert clamp(-0.1, 0.0, 1.0) == pytest.approx(0.0)

    def test_float_above_hi(self):
        assert clamp(1.1, 0.0, 1.0) == pytest.approx(1.0)

    def test_lo_equals_hi(self):
        # Degenerate range: value is clamped to the single point
        assert clamp(7, 5, 5) == 5


# ---------------------------------------------------------------------------
# encode_html
# ---------------------------------------------------------------------------

class TestEncodeHtml:
    """encode_html must escape characters unsafe in SVG/HTML text nodes."""

    def test_escapes_less_than(self):
        result = encode_html("<")
        assert "<" not in result
        assert "&lt;" in result

    def test_escapes_greater_than(self):
        result = encode_html(">")
        assert ">" not in result
        assert "&gt;" in result

    def test_escapes_ampersand(self):
        result = encode_html("&")
        assert result == "&amp;"

    def test_escapes_double_quote(self):
        result = encode_html('"')
        assert '"' not in result
        assert "&quot;" in result

    def test_escapes_single_quote(self):
        result = encode_html("'")
        assert "'" not in result
        # Must use a numeric or named entity (decimal &#39; or hex &#x27; or &apos;)
        assert "&#39;" in result or "&#x27;" in result or "&apos;" in result

    def test_script_tag_is_fully_escaped(self):
        result = encode_html("<script>")
        assert "<script>" not in result
        assert "&lt;" in result
        assert "&gt;" in result

    def test_xss_vector(self):
        payload = '<img src=x onerror="alert(1)">'
        result = encode_html(payload)
        assert "<" not in result
        assert ">" not in result
        assert '"' not in result

    def test_plain_text_unchanged(self):
        assert encode_html("hello world") == "hello world"

    def test_empty_string(self):
        assert encode_html("") == ""

    def test_non_ascii_escaped_numerically(self):
        # Characters above U+007F must be numeric-escaped
        result = encode_html("☃")  # snowman
        assert "☃" not in result
        assert "&#" in result

    def test_combined_string(self):
        result = encode_html("1 < 2 & 3 > 0")
        assert "&lt;" in result
        assert "&amp;" in result
        assert "&gt;" in result
        assert "<" not in result
        assert ">" not in result
        assert "&" not in result.replace("&lt;", "").replace("&amp;", "").replace("&gt;", "")
