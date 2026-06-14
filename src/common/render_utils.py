"""
render_utils.py -- SVG/text rendering utilities.

Covers number formatting, text measurement, HTML escaping, layout helpers,
and word-wrapping.  No third-party imports.

Import convention: deployment root is src/; siblings imported without src. prefix.
"""

from __future__ import annotations

import html
import math
from typing import TypeVar

# ---------------------------------------------------------------------------
# Number formatting
# ---------------------------------------------------------------------------

def k_formatter(num: float) -> str:
    """
    Abbreviate a number the same way github-readme-stats kFormatter does.

    - < 1 000   -> plain integer string (e.g. "42")
    - >= 1 000  -> "<n>k" with 1 decimal, trailing .0 stripped (e.g. "1.5k")
    - >= 1 000 000 -> "<n>m" with 1 decimal, trailing .0 stripped
    """
    num = float(num)
    if abs(num) >= 1_000_000:
        val = round(num / 1_000_000, 1)
        suffix = "m"
    elif abs(num) >= 1_000:
        val = round(num / 1_000, 1)
        suffix = "k"
    else:
        return str(int(round(num)))

    # Strip trailing .0 to match JS behaviour: 1000 -> "1k" not "1.0k"
    formatted = f"{val:.1f}"
    if formatted.endswith(".0"):
        formatted = formatted[:-2]
    return formatted + suffix


def format_number(
    num: float,
    number_format: str = "short",
    precision: int = 1,
) -> str:
    """
    Format a number for display.

    - "short": abbreviated with k/m suffix, *precision* decimal places
      (delegates to k_formatter-style logic).
    - "long": full integer with comma thousands-separators.
    """
    num = float(num)
    if number_format == "long":
        return f"{int(round(num)):,}"

    # "short" (default) -- respects precision
    if abs(num) >= 1_000_000:
        val = round(num / 1_000_000, precision)
        suffix = "m"
    elif abs(num) >= 1_000:
        val = round(num / 1_000, precision)
        suffix = "k"
    else:
        return str(int(round(num)))

    fmt = f"{val:.{precision}f}"
    # Strip trailing .0 only when precision is exactly 1 (matches kFormatter)
    if precision == 1 and fmt.endswith(".0"):
        fmt = fmt[:-2]
    return fmt + suffix


# ---------------------------------------------------------------------------
# Text measurement
# ---------------------------------------------------------------------------

# Per-character approximate advance widths at font-size 10px (Verdana-ish).
# Values derived from common character-width tables used in the original JS.
# Scaled proportionally for any other font size via (font_size / 10).
_CHAR_WIDTHS: dict[str, float] = {
    " ": 2.95,
    "!": 3.32,
    '"': 4.21,
    "#": 6.63,
    "$": 5.53,
    "%": 8.32,
    "&": 7.22,
    "'": 2.42,
    "(": 3.87,
    ")": 3.87,
    "*": 5.53,
    "+": 6.63,
    ",": 2.95,
    "-": 3.87,
    ".": 2.95,
    "/": 4.43,
    "0": 6.08,
    "1": 6.08,
    "2": 6.08,
    "3": 6.08,
    "4": 6.08,
    "5": 6.08,
    "6": 6.08,
    "7": 6.08,
    "8": 6.08,
    "9": 6.08,
    ":": 3.32,
    ";": 3.32,
    "<": 6.63,
    "=": 6.63,
    ">": 6.63,
    "?": 4.97,
    "@": 10.23,
    "A": 7.22,
    "B": 6.63,
    "C": 6.63,
    "D": 7.22,
    "E": 5.53,
    "F": 5.53,
    "G": 7.22,
    "H": 7.22,
    "I": 2.76,
    "J": 3.87,
    "K": 6.63,
    "L": 5.53,
    "M": 8.32,
    "N": 7.22,
    "O": 7.77,
    "P": 5.53,
    "Q": 7.77,
    "R": 6.08,
    "S": 5.53,
    "T": 5.53,
    "U": 7.22,
    "V": 7.22,
    "W": 9.96,
    "X": 6.63,
    "Y": 6.08,
    "Z": 6.08,
    "[": 3.87,
    "\\": 4.43,
    "]": 3.87,
    "^": 6.63,
    "_": 5.53,
    "`": 4.43,
    "a": 5.53,
    "b": 5.53,
    "c": 4.97,
    "d": 5.53,
    "e": 5.53,
    "f": 2.76,
    "g": 5.53,
    "h": 5.53,
    "i": 2.20,
    "j": 2.20,
    "k": 4.97,
    "l": 2.20,
    "m": 8.32,
    "n": 5.53,
    "o": 5.53,
    "p": 5.53,
    "q": 5.53,
    "r": 3.32,
    "s": 4.43,
    "t": 3.87,
    "u": 5.53,
    "v": 4.97,
    "w": 7.22,
    "x": 4.97,
    "y": 4.97,
    "z": 4.43,
    "{": 3.87,
    "|": 2.95,
    "}": 3.87,
    "~": 6.63,
}

_DEFAULT_CHAR_WIDTH = 5.53  # fallback for unmapped characters


def measure_text(text: str, font_size: float = 10) -> float:
    """
    Approximate the rendered pixel width of *text* at the given *font_size*.

    Uses a per-character advance-width table calibrated at 10 px; results are
    scaled linearly for other sizes.  Suitable for layout decisions; not a
    substitute for actual text-metrics from a renderer.
    """
    scale = font_size / 10.0
    total = sum(_CHAR_WIDTHS.get(ch, _DEFAULT_CHAR_WIDTH) for ch in text)
    return total * scale


# ---------------------------------------------------------------------------
# HTML / SVG escaping
# ---------------------------------------------------------------------------

def encode_html(s: str) -> str:
    """
    Escape a string for safe embedding in SVG text nodes or attributes.

    Escapes &, <, >, ", ' using named references, then numeric-escapes any
    remaining non-ASCII characters.
    """
    # html.escape handles & < > " but NOT '
    escaped = html.escape(s, quote=True)
    # html.escape with quote=True uses &quot; for " but leaves ' as-is
    # Replace literal apostrophe with named entity
    escaped = escaped.replace("'", "&#39;")

    # Numeric-escape non-ASCII
    result: list[str] = []
    for ch in escaped:
        if ord(ch) > 127:
            result.append(f"&#{ord(ch)};")
        else:
            result.append(ch)
    return "".join(result)


# ---------------------------------------------------------------------------
# Numeric clamping
# ---------------------------------------------------------------------------

_T = TypeVar("_T", int, float)


def clamp(value: _T, lo: _T, hi: _T) -> _T:
    """Return *value* clamped to the inclusive range [*lo*, *hi*]."""
    return max(lo, min(value, hi))


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def flex_layout(
    items: list[str],
    gap: float,
    direction: str = "row",
) -> list[str]:
    """
    Position SVG items in a row or column with a fixed *gap* between them.

    Returns each item wrapped in a ``<g transform="translate(x, y)">`` element
    placed cumulatively along the chosen *direction*.

    - ``direction="row"``    -- items advance along the X axis
    - ``direction="column"`` -- items advance along the Y axis
    """
    result: list[str] = []
    offset: float = 0.0
    for item in items:
        if direction == "column":
            tx, ty = 0.0, offset
        else:
            tx, ty = offset, 0.0
        result.append(f'<g transform="translate({tx}, {ty})">{item}</g>')
        offset += gap
    return result


# ---------------------------------------------------------------------------
# Word wrapping
# ---------------------------------------------------------------------------

def wrap_text_multiline(
    text: str,
    width: int = 59,
    max_lines: int = 3,
) -> list[str]:
    """
    Word-wrap *text* into up to *max_lines* lines of at most *width* characters.

    If the text is truncated an ellipsis is appended to the last line.
    Words longer than *width* are placed alone on their own line (they will
    overflow the column, matching the JS behaviour of not splitting words).
    """
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        # +1 for the space separator (except first word on a line)
        needed = len(word) if not current else current_len + 1 + len(word)
        if needed <= width:
            current.append(word)
            current_len = needed
        else:
            if current:
                lines.append(" ".join(current))
            if len(lines) >= max_lines:
                break
            current = [word]
            current_len = len(word)

    # Flush any remaining words
    if current and len(lines) < max_lines:
        lines.append(" ".join(current))

    truncated = len(lines) == max_lines and (
        # There are still words that haven't been placed
        bool(current) and " ".join(current) not in lines
        or (words and lines and " ".join(words) != " ".join(
            " ".join(l.split()) for l in lines
        ))
    )

    # Simpler truncation check: reconstruct and compare
    reconstructed = " ".join(lines)
    if reconstructed != text.rstrip():
        truncated = True

    if truncated and lines:
        last = lines[-1]
        # Trim last line to make room for ellipsis if needed
        if len(last) + 3 > width:
            last = last[: max(0, width - 3)].rstrip()
        lines[-1] = last + "..."

    return lines
