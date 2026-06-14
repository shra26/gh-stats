"""
wakatime_card.py -- Renders a WakaTime Stats SVG card.

Layouts:
  - default : per-language rows with name, progress bar, time/percent label (FULL)
  - compact  : stacked bar + two-column legend (FULL)

Import convention: deployment root is src/; siblings imported without src. prefix.
"""

from __future__ import annotations

import math
from typing import Any

from cards.base_card import Card
from common.colors import get_card_colors
from common.render_utils import encode_html, clamp

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CARD_WIDTH = 495
_ROW_HEIGHT = 40
_BAR_HEIGHT = 8
_COMPACT_BAR_Y = 35
_COMPACT_BAR_HEIGHT = 8
_COMPACT_LEGEND_START_Y = 60
_COMPACT_LEGEND_ROW_H = 20
_MAX_LANGS = 20

# A small palette for languages that do not carry a color from the API
_FALLBACK_COLORS = [
    "#2965f1", "#e34c26", "#f1e05a", "#563d7c", "#b07219",
    "#00b4ab", "#375eab", "#da5b0b", "#4f5d95", "#3572A5",
]


def _parse_list_option(val: Any) -> list[str]:
    if isinstance(val, list):
        return [str(v).lower() for v in val]
    if isinstance(val, str) and val:
        return [v.strip().lower() for v in val.split(",") if v.strip()]
    return []


def _lang_color(lang: dict, index: int) -> str:
    color = lang.get("color") or ""
    if color and color.startswith("#"):
        return color
    return _FALLBACK_COLORS[index % len(_FALLBACK_COLORS)]


# ---------------------------------------------------------------------------
# Layout renderers
# ---------------------------------------------------------------------------

def _render_default(
    langs: list[dict],
    colors: dict,
    hide_progress: bool,
    display_format: str,
    line_height: int,
    card_width: int,
) -> tuple[str, int]:
    """
    Default layout: one row per language.
    Returns (body_svg, total_height).
    """
    text_color = colors["textColor"]
    bar_width = card_width - 80
    parts: list[str] = []
    row_h = line_height if line_height else _ROW_HEIGHT
    y = 0

    for i, lang in enumerate(langs):
        color = _lang_color(lang, i)
        name = encode_html(lang.get("name", ""))
        pct = lang.get("percent", 0.0)

        if display_format == "percent":
            label = f"{pct:.1f}%"
        else:
            # Default: time text from WakaTime (e.g. "3 hrs 22 mins")
            label = encode_html(lang.get("text", f"{pct:.1f}%"))

        # Name on the left
        parts.append(
            f'<text x="0" y="{y + 15}" fill="{text_color}" font-size="11" '
            f'font-family="Segoe UI,Ubuntu,sans-serif">{name}</text>'
        )

        if not hide_progress:
            # Time/percent label on the right
            parts.append(
                f'<text x="{bar_width + 48}" y="{y + 15}" fill="{text_color}" '
                f'font-size="11" font-family="Segoe UI,Ubuntu,sans-serif" '
                f'text-anchor="end">{label}</text>'
            )
            # Background bar
            parts.append(
                f'<rect x="0" y="{y + 22}" rx="4" ry="4" '
                f'width="{bar_width}" height="{_BAR_HEIGHT}" fill="#ddd" opacity="0.5"/>'
            )
            # Filled bar
            filled = max(0.0, pct / 100.0 * bar_width)
            parts.append(
                f'<rect x="0" y="{y + 22}" rx="4" ry="4" '
                f'width="{filled:.2f}" height="{_BAR_HEIGHT}" fill="{color}"/>'
            )

        y += row_h

    return "\n".join(parts), y


def _render_compact(
    langs: list[dict],
    colors: dict,
    hide_progress: bool,
    display_format: str,
    card_width: int,
) -> tuple[str, int]:
    """
    Compact layout: stacked bar + two-column legend.
    Returns (body_svg, total_height).
    """
    text_color = colors["textColor"]
    bar_width = card_width - 50
    parts: list[str] = []

    if not hide_progress:
        # Stacked progress bar
        parts.append(
            f'<rect x="0" y="{_COMPACT_BAR_Y}" rx="4" ry="4" '
            f'width="{bar_width}" height="{_COMPACT_BAR_HEIGHT}" fill="#ddd" opacity="0.5"/>'
        )
        x_off = 0.0
        for i, lang in enumerate(langs):
            color = _lang_color(lang, i)
            pct = lang.get("percent", 0.0)
            seg_w = pct / 100.0 * bar_width
            if seg_w < 0.5:
                continue
            parts.append(
                f'<rect x="{x_off:.2f}" y="{_COMPACT_BAR_Y}" '
                f'width="{seg_w:.2f}" height="{_COMPACT_BAR_HEIGHT}" '
                f'fill="{color}"/>'
            )
            x_off += seg_w

    # Legend grid (two columns)
    col_width = bar_width / 2
    for i, lang in enumerate(langs):
        pct = lang.get("percent", 0.0)
        color = _lang_color(lang, i)
        name = encode_html(lang.get("name", ""))
        if display_format == "percent":
            label = f"{pct:.1f}%"
        else:
            label = encode_html(lang.get("text", f"{pct:.1f}%"))
        col = i % 2
        row = i // 2
        x = col * col_width
        y = _COMPACT_LEGEND_START_Y + row * _COMPACT_LEGEND_ROW_H

        parts.append(
            f'<circle cx="{x + 5:.1f}" cy="{y + 6:.1f}" r="5" fill="{color}"/>'
            f'<text x="{x + 15:.1f}" y="{y + 10:.1f}" '
            f'fill="{text_color}" font-size="11" font-family="Segoe UI,Ubuntu,sans-serif">'
            f'{name}'
        )
        if not hide_progress:
            parts.append(
                f' <tspan fill="{text_color}" opacity="0.7">{label}</tspan>'
            )
        parts.append("</text>")

    legend_rows = math.ceil(len(langs) / 2)
    total_h = _COMPACT_LEGEND_START_Y + legend_rows * _COMPACT_LEGEND_ROW_H + 10
    return "\n".join(parts), total_h


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_wakatime_card(wakatime: dict, options: dict | None = None) -> str:
    """
    Render a WakaTime Stats SVG card.

    Parameters
    ----------
    wakatime:
        The WakaTime stats "data" dict. Expected to contain a "languages" list
        of {name, percent, text, total_seconds, color?}.
    options:
        Raw query-param dict.

    Returns
    -------
    str
        Complete SVG markup.
    """
    opts: dict = options or {}

    layout: str = opts.get("layout", "default") or "default"
    hide_list: list[str] = _parse_list_option(opts.get("hide"))
    hide_title: bool = str(opts.get("hide_title", "false")).lower() == "true"
    hide_border: bool = str(opts.get("hide_border", "false")).lower() == "true"
    hide_progress: bool = str(opts.get("hide_progress", "false")).lower() == "true"
    disable_animations: bool = (
        str(opts.get("disable_animations", "false")).lower() == "true"
    )
    display_format: str = opts.get("display_format", "time") or "time"
    custom_title: str | None = opts.get("custom_title")

    try:
        langs_count = clamp(int(opts.get("langs_count", _MAX_LANGS)), 1, _MAX_LANGS)
    except (TypeError, ValueError):
        langs_count = _MAX_LANGS

    try:
        card_width = int(opts.get("card_width") or 0)
    except (TypeError, ValueError):
        card_width = 0
    if not card_width:
        card_width = _CARD_WIDTH

    try:
        line_height = int(opts.get("line_height", _ROW_HEIGHT))
    except (TypeError, ValueError):
        line_height = _ROW_HEIGHT

    try:
        border_radius = float(opts.get("border_radius", 4.5))
    except (TypeError, ValueError):
        border_radius = 4.5

    colors = get_card_colors(
        title_color=opts.get("title_color"),
        icon_color=opts.get("icon_color"),
        text_color=opts.get("text_color"),
        bg_color=opts.get("bg_color"),
        border_color=opts.get("border_color"),
        theme=opts.get("theme"),
    )

    # Filter and slice languages
    raw_langs: list[dict] = wakatime.get("languages", [])
    filtered: list[dict] = [
        lang for lang in raw_langs
        if lang.get("name", "").lower() not in hide_list
        and lang.get("total_seconds", 0) > 0
    ]
    langs = filtered[:langs_count]

    # Empty state
    if not langs:
        card = Card(
            width=card_width,
            height=150,
            border_radius=border_radius,
            colors=colors,
            custom_title=custom_title,
            default_title="WakaTime Stats",
        )
        if hide_border:
            card.set_hide_border(True)
        if hide_title:
            card.set_hide_title(True)
        if disable_animations:
            card.disable_animations()
        body = (
            f'<text x="{card_width // 2}" y="75" text-anchor="middle" '
            f'fill="{colors["textColor"]}" font-size="11" '
            f'font-family="Segoe UI,Ubuntu,sans-serif">No WakaTime data available</text>'
        )
        return card.render(body)

    # Render chosen layout
    if layout == "compact":
        body_svg, content_h = _render_compact(
            langs, colors, hide_progress, display_format, card_width
        )
    else:
        body_svg, content_h = _render_default(
            langs, colors, hide_progress, display_format, line_height, card_width
        )

    title_offset = 0 if hide_title else 45
    card_height = content_h + title_offset + 20

    card = Card(
        width=card_width,
        height=card_height,
        border_radius=border_radius,
        colors=colors,
        custom_title=custom_title,
        default_title="WakaTime Stats",
    )
    if hide_border:
        card.set_hide_border(True)
    if hide_title:
        card.set_hide_title(True)
    if disable_animations:
        card.disable_animations()

    wrapped_body = (
        f'<g transform="translate(25, {title_offset})">'
        f'{body_svg}'
        f'</g>'
    )
    return card.render(wrapped_body)
