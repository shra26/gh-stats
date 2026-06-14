"""
colors.py -- hex color validation, gradient parsing, and theme-aware card color resolution.

Import convention: deployment root is src/; siblings imported without src. prefix.
"""

from __future__ import annotations

import re
from typing import Union

from themes import THEMES


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_HEX_RE = re.compile(
    r"^([A-Fa-f0-9]{8}|[A-Fa-f0-9]{6}|[A-Fa-f0-9]{4}|[A-Fa-f0-9]{3})$"
)


def is_valid_hex_color(color: str) -> bool:
    """Return True if *color* is a bare hex color string (3/4/6/8 digits, no '#')."""
    if not isinstance(color, str):
        return False
    return bool(_HEX_RE.match(color))


def is_valid_gradient(parts: list[str]) -> bool:
    """
    Return True if *parts* represents a valid gradient spec.

    A gradient has more than 2 elements: the first element is a rotation angle
    (not validated) and every subsequent element must be a valid hex color.
    """
    if len(parts) <= 2:
        return False
    return all(is_valid_hex_color(p) for p in parts[1:])


# ---------------------------------------------------------------------------
# Color resolution
# ---------------------------------------------------------------------------

def fallback_color(
    color: str | None,
    fallback: str,
) -> Union[str, list[str]]:
    """
    Resolve a raw query-param color value to a usable color.

    - If *color* contains commas and parses as a valid gradient, return the
      parts list: [angle, c1, c2, ...].
    - If *color* is a bare valid hex, return '#' + color.
    - Otherwise return *fallback* (which is already a full '#...' string).
    """
    if color is None:
        return fallback

    parts = [p.strip() for p in color.split(",")]

    if len(parts) > 1:
        if is_valid_gradient(parts):
            return parts  # gradient: [angle, c1, c2, ...]
        return fallback

    # Single value
    if is_valid_hex_color(color.strip()):
        return "#" + color.strip()

    return fallback


# ---------------------------------------------------------------------------
# Card color resolution
# ---------------------------------------------------------------------------

def get_card_colors(
    *,
    title_color: str | None = None,
    text_color: str | None = None,
    icon_color: str | None = None,
    bg_color: str | None = None,
    border_color: str | None = None,
    ring_color: str | None = None,
    theme: str | None = None,
) -> dict:
    """
    Resolve all card colors respecting the precedence:
        query param > selected theme > default theme.

    *ring_color* falls back to the resolved *title_color* (not the default
    theme) when neither the query param nor the selected theme provides one.

    Returns a dict with camelCase keys:
        titleColor, textColor, iconColor, bgColor, borderColor, ringColor

    *bgColor* may be a list[str] for gradient specs; all other values are
    strings.  Raises ValueError if a non-bg color resolves to a non-string.
    """
    selected: dict = THEMES.get(theme, THEMES["default"]) if theme else THEMES["default"]
    default_theme: dict = THEMES["default"]

    def _resolve(user_val: str | None, theme_key: str) -> Union[str, list[str]]:
        # User param takes precedence, then selected theme, then default theme.
        raw = user_val or selected.get(theme_key) or default_theme[theme_key]
        fb = "#" + default_theme[theme_key]
        return fallback_color(raw, fb)

    title = _resolve(title_color, "title_color")
    text = _resolve(text_color, "text_color")
    icon = _resolve(icon_color, "icon_color")
    border = _resolve(border_color, "border_color")

    # bg_color is the only field that may return a list (gradient)
    bg_raw = bg_color or selected.get("bg_color") or default_theme["bg_color"]
    bg_fb = "#" + default_theme["bg_color"]
    bg = fallback_color(bg_raw, bg_fb)

    # ring_color: user param > selected theme ring_color > resolved title_color
    ring_raw = ring_color or selected.get("ring_color")
    if ring_raw:
        ring_fb = "#" + default_theme.get("ring_color", default_theme["title_color"])
        ring = fallback_color(ring_raw, ring_fb)
    else:
        # Fall back to the already-resolved title color
        ring = title

    # Validate: non-bg colors must be strings
    for name, val in [
        ("titleColor", title),
        ("textColor", text),
        ("iconColor", icon),
        ("borderColor", border),
        ("ringColor", ring),
    ]:
        if not isinstance(val, str):
            raise ValueError(
                f"{name} resolved to a non-string value {val!r}; "
                "only bgColor may be a gradient list"
            )

    return {
        "titleColor": title,
        "textColor": text,
        "iconColor": icon,
        "bgColor": bg,
        "borderColor": border,
        "ringColor": ring,
    }
