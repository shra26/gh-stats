"""
top_langs_card.py -- Renders the Top Languages SVG card.

Layouts implemented:
  - normal   : per-language rows with labeled progress bars (FULL)
  - compact  : single stacked bar + two-column legend grid (FULL)
  - donut    : segmented donut SVG arcs (FULL)
  - donut-vertical : same as donut (FULL)
  - pie      : filled pie arcs (FULL)

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

_NORMAL_DEFAULT_COUNT = 5
_OTHER_DEFAULT_COUNT = 6
_MAX_LANGS = 20
_CARD_WIDTH = 300
_COMPACT_CARD_WIDTH = 400
_BAR_HEIGHT = 8
_LANG_ROW_HEIGHT = 40
_COMPACT_HEADER_Y = 25
_COMPACT_BAR_Y = 35
_COMPACT_BAR_HEIGHT = 8
_COMPACT_LEGEND_START_Y = 60
_COMPACT_LEGEND_ROW_H = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_list_option(val: Any) -> list[str]:
    if isinstance(val, list):
        return [str(v).lower() for v in val]
    if isinstance(val, str) and val:
        return [v.strip().lower() for v in val.split(",") if v.strip()]
    return []


def _lang_color(color: str | None) -> str:
    return color if color else "#858585"


def _pct_label(pct: float, stats_format: str, lang: dict) -> str:
    if stats_format == "bytes":
        size = lang.get("size", 0)
        if size >= 1_000_000:
            return f"{size/1_000_000:.2f} MB"
        if size >= 1_000:
            return f"{size/1_000:.2f} kB"
        return f"{size} B"
    return f"{pct:.2f}%"


# ---------------------------------------------------------------------------
# SVG arc helpers for donut/pie
# ---------------------------------------------------------------------------

def _polar(cx: float, cy: float, r: float, angle_deg: float) -> tuple[float, float]:
    rad = math.radians(angle_deg)
    return cx + r * math.cos(rad), cy + r * math.sin(rad)


def _arc_path(
    cx: float,
    cy: float,
    r: float,
    start_deg: float,
    end_deg: float,
) -> str:
    """SVG arc path for a pie/donut slice."""
    # Clamp to avoid full-circle degenerate arc
    delta = min(end_deg - start_deg, 359.999)
    x1, y1 = _polar(cx, cy, r, start_deg)
    x2, y2 = _polar(cx, cy, r, start_deg + delta)
    large_arc = 1 if delta > 180 else 0
    return (
        f"M {cx:.2f} {cy:.2f} "
        f"L {x1:.2f} {y1:.2f} "
        f"A {r:.2f} {r:.2f} 0 {large_arc} 1 {x2:.2f} {y2:.2f} Z"
    )


def _donut_arc_path(
    cx: float,
    cy: float,
    r_outer: float,
    r_inner: float,
    start_deg: float,
    end_deg: float,
) -> str:
    """SVG donut arc path (outer arc forward, inner arc backward)."""
    delta = min(end_deg - start_deg, 359.999)
    large_arc = 1 if delta > 180 else 0
    ox1, oy1 = _polar(cx, cy, r_outer, start_deg)
    ox2, oy2 = _polar(cx, cy, r_outer, start_deg + delta)
    ix1, iy1 = _polar(cx, cy, r_inner, start_deg + delta)
    ix2, iy2 = _polar(cx, cy, r_inner, start_deg)
    return (
        f"M {ox1:.2f} {oy1:.2f} "
        f"A {r_outer:.2f} {r_outer:.2f} 0 {large_arc} 1 {ox2:.2f} {oy2:.2f} "
        f"L {ix1:.2f} {iy1:.2f} "
        f"A {r_inner:.2f} {r_inner:.2f} 0 {large_arc} 0 {ix2:.2f} {iy2:.2f} Z"
    )


# ---------------------------------------------------------------------------
# Layout renderers
# ---------------------------------------------------------------------------

def _render_normal(
    langs: list[dict],
    colors: dict,
    hide_progress: bool,
    stats_format: str,
    card_width: int,
) -> tuple[str, int]:
    """
    Normal layout: one row per language with a labeled progress bar.
    Returns (body_svg, total_height).
    """
    text_color = colors["textColor"]
    rows: list[str] = []
    y = 0

    for lang in langs:
        pct = lang["pct"]
        color = _lang_color(lang.get("color"))
        name = encode_html(lang["name"])
        label = _pct_label(pct, stats_format, lang)
        bar_width = card_width - 50

        if hide_progress:
            row = (
                f'<text x="2" y="{y + 15}" class="lang-name" '
                f'fill="{text_color}" font-size="11" font-family="Segoe UI,Ubuntu,sans-serif">'
                f'{name}</text>'
            )
        else:
            row = (
                f'<text x="2" y="{y + 15}" class="lang-name" '
                f'fill="{text_color}" font-size="11" font-family="Segoe UI,Ubuntu,sans-serif">'
                f'{name}</text>'
                f'<text x="{bar_width}" y="{y + 15}" '
                f'fill="{text_color}" font-size="11" font-family="Segoe UI,Ubuntu,sans-serif" '
                f'text-anchor="end">{encode_html(label)}</text>'
                f'<rect x="2" y="{y + 22}" rx="4" ry="4" width="{bar_width}" height="{_BAR_HEIGHT}" '
                f'fill="#ddd" opacity="0.5"/>'
                f'<rect x="2" y="{y + 22}" rx="4" ry="4" '
                f'width="{max(0, pct / 100 * bar_width):.2f}" height="{_BAR_HEIGHT}" '
                f'fill="{color}"/>'
            )

        rows.append(row)
        y += _LANG_ROW_HEIGHT

    body = "\n".join(rows)
    return body, y


def _render_compact(
    langs: list[dict],
    colors: dict,
    hide_progress: bool,
    stats_format: str,
    card_width: int,
) -> tuple[str, int]:
    """
    Compact layout: stacked bar on top + two-column legend.
    Returns (body_svg, total_height).
    """
    text_color = colors["textColor"]
    bar_width = card_width - 50
    parts: list[str] = []

    if not hide_progress:
        # Stacked bar
        parts.append(
            f'<rect x="0" y="{_COMPACT_BAR_Y}" rx="4" ry="4" '
            f'width="{bar_width}" height="{_COMPACT_BAR_HEIGHT}" fill="#ddd" opacity="0.5"/>'
        )
        x_offset = 0.0
        for lang in langs:
            pct = lang["pct"]
            color = _lang_color(lang.get("color"))
            seg_w = pct / 100 * bar_width
            if seg_w < 0.5:
                continue
            parts.append(
                f'<rect x="{x_offset:.2f}" y="{_COMPACT_BAR_Y}" '
                f'width="{seg_w:.2f}" height="{_COMPACT_BAR_HEIGHT}" '
                f'fill="{color}"/>'
            )
            x_offset += seg_w

    # Legend grid (two columns)
    col_width = bar_width / 2
    for i, lang in enumerate(langs):
        pct = lang["pct"]
        color = _lang_color(lang.get("color"))
        name = encode_html(lang["name"])
        label = _pct_label(pct, stats_format, lang)
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
                f' <tspan fill="{text_color}" opacity="0.7">{encode_html(label)}</tspan>'
            )
        parts.append("</text>")

    legend_rows = math.ceil(len(langs) / 2)
    total_h = _COMPACT_LEGEND_START_Y + legend_rows * _COMPACT_LEGEND_ROW_H + 10
    return "\n".join(parts), total_h


def _render_donut(
    langs: list[dict],
    colors: dict,
    hide_progress: bool,
    stats_format: str,
    card_width: int,
    vertical: bool = False,
) -> tuple[str, int]:
    """
    Donut layout: segmented donut + legend.
    'vertical' flag is accepted but renders identically (legend below in both cases).
    """
    text_color = colors["textColor"]
    cx, cy = card_width // 2, 80
    r_outer, r_inner = 60.0, 35.0
    gap_deg = 2.0

    parts: list[str] = []
    angle = -90.0

    for lang in langs:
        pct = lang["pct"]
        color = _lang_color(lang.get("color"))
        sweep = pct / 100 * 360 - gap_deg
        if sweep <= 0:
            continue
        d = _donut_arc_path(cx, cy, r_outer, r_inner, angle, angle + sweep)
        parts.append(f'<path d="{d}" fill="{color}"/>')
        angle += pct / 100 * 360

    # Legend below the donut
    legend_y = cy + r_outer + 20
    col_width = (card_width - 40) / 2
    for i, lang in enumerate(langs):
        pct = lang["pct"]
        color = _lang_color(lang.get("color"))
        name = encode_html(lang["name"])
        label = _pct_label(pct, stats_format, lang)
        col = i % 2
        row = i // 2
        x = 20 + col * col_width
        y = legend_y + row * _COMPACT_LEGEND_ROW_H

        parts.append(
            f'<circle cx="{x + 5:.1f}" cy="{y + 6:.1f}" r="5" fill="{color}"/>'
            f'<text x="{x + 15:.1f}" y="{y + 10:.1f}" '
            f'fill="{text_color}" font-size="11" font-family="Segoe UI,Ubuntu,sans-serif">'
            f'{name}'
        )
        if not hide_progress:
            parts.append(f' <tspan opacity="0.7">{encode_html(label)}</tspan>')
        parts.append("</text>")

    legend_rows = math.ceil(len(langs) / 2)
    total_h = legend_y + legend_rows * _COMPACT_LEGEND_ROW_H + 10
    return "\n".join(parts), total_h


def _render_pie(
    langs: list[dict],
    colors: dict,
    hide_progress: bool,
    stats_format: str,
    card_width: int,
) -> tuple[str, int]:
    """Pie layout: filled pie arcs + legend."""
    text_color = colors["textColor"]
    cx, cy = card_width // 2, 80
    r = 65.0
    gap_deg = 1.5

    parts: list[str] = []
    angle = -90.0

    for lang in langs:
        pct = lang["pct"]
        color = _lang_color(lang.get("color"))
        sweep = pct / 100 * 360 - gap_deg
        if sweep <= 0:
            continue
        d = _arc_path(cx, cy, r, angle, angle + sweep)
        parts.append(f'<path d="{d}" fill="{color}"/>')
        angle += pct / 100 * 360

    legend_y = cy + r + 20
    col_width = (card_width - 40) / 2
    for i, lang in enumerate(langs):
        pct = lang["pct"]
        color = _lang_color(lang.get("color"))
        name = encode_html(lang["name"])
        label = _pct_label(pct, stats_format, lang)
        col = i % 2
        row = i // 2
        x = 20 + col * col_width
        y = legend_y + row * _COMPACT_LEGEND_ROW_H

        parts.append(
            f'<circle cx="{x + 5:.1f}" cy="{y + 6:.1f}" r="5" fill="{color}"/>'
            f'<text x="{x + 15:.1f}" y="{y + 10:.1f}" '
            f'fill="{text_color}" font-size="11" font-family="Segoe UI,Ubuntu,sans-serif">'
            f'{name}'
        )
        if not hide_progress:
            parts.append(f' <tspan opacity="0.7">{encode_html(label)}</tspan>')
        parts.append("</text>")

    legend_rows = math.ceil(len(langs) / 2)
    total_h = legend_y + legend_rows * _COMPACT_LEGEND_ROW_H + 10
    return "\n".join(parts), total_h


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_top_languages_card(
    top_langs: dict,
    options: dict | None = None,
) -> str:
    """
    Render a Top Languages SVG card.

    Parameters
    ----------
    top_langs:
        Mapping of lang name -> {name, color, size, count}, already ranked.
    options:
        Raw query-param dict. Recognised keys mirror the /api/top-langs param spec.

    Returns
    -------
    str
        Complete SVG markup.
    """
    opts: dict = options or {}

    layout: str = opts.get("layout", "normal") or "normal"
    hide_list: list[str] = _parse_list_option(opts.get("hide"))
    hide_title: bool = str(opts.get("hide_title", "false")).lower() == "true"
    hide_border: bool = str(opts.get("hide_border", "false")).lower() == "true"
    hide_progress: bool = str(opts.get("hide_progress", "false")).lower() == "true"
    disable_animations: bool = (
        str(opts.get("disable_animations", "false")).lower() == "true"
    )
    stats_format: str = opts.get("stats_format", "percentages") or "percentages"
    custom_title: str | None = opts.get("custom_title")

    default_count = _NORMAL_DEFAULT_COUNT if layout == "normal" else _OTHER_DEFAULT_COUNT
    try:
        langs_count = int(opts.get("langs_count", default_count))
    except (TypeError, ValueError):
        langs_count = default_count
    langs_count = clamp(langs_count, 1, _MAX_LANGS)

    try:
        card_width = int(opts.get("card_width") or 0)
    except (TypeError, ValueError):
        card_width = 0
    if not card_width:
        card_width = _COMPACT_CARD_WIDTH if layout == "compact" else _CARD_WIDTH

    try:
        border_radius = float(opts.get("border_radius", 4.5))
    except (TypeError, ValueError):
        border_radius = 4.5

    colors = get_card_colors(
        title_color=opts.get("title_color"),
        text_color=opts.get("text_color"),
        bg_color=opts.get("bg_color"),
        border_color=opts.get("border_color"),
        theme=opts.get("theme"),
    )

    # Filter and rank languages
    filtered: list[dict] = []
    total_size = 0
    for name, lang in top_langs.items():
        if name.lower() in hide_list:
            continue
        filtered.append({
            "name": lang.get("name", name),
            "color": lang.get("color"),
            "size": lang.get("size", 0),
            "count": lang.get("count", 0),
        })
        total_size += lang.get("size", 0)

    if not filtered or total_size == 0:
        # Return an empty-state card
        card = Card(
            width=card_width,
            height=150,
            border_radius=border_radius,
            colors=colors,
            custom_title=custom_title,
            default_title="Most Used Languages",
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
            f'font-family="Segoe UI,Ubuntu,sans-serif">No languages detected</text>'
        )
        return card.render(body)

    # Compute percentages and trim
    for lang in filtered:
        lang["pct"] = lang["size"] / total_size * 100

    filtered.sort(key=lambda l: l["size"], reverse=True)
    langs = filtered[:langs_count]

    # Re-normalise percentages to the visible set
    visible_total = sum(l["pct"] for l in langs)
    if visible_total > 0:
        for lang in langs:
            lang["pct"] = lang["pct"] / visible_total * 100

    # Pick layout renderer
    if layout == "compact":
        body, content_h = _render_compact(
            langs, colors, hide_progress, stats_format, card_width
        )
    elif layout in ("donut", "donut-vertical"):
        body, content_h = _render_donut(
            langs, colors, hide_progress, stats_format, card_width,
            vertical=(layout == "donut-vertical"),
        )
    elif layout == "pie":
        body, content_h = _render_pie(
            langs, colors, hide_progress, stats_format, card_width
        )
    else:
        # Default: normal
        body, content_h = _render_normal(
            langs, colors, hide_progress, stats_format, card_width
        )

    # base_card.render() wraps body in translate(25, 50) when title is visible,
    # translate(25, 0) when hidden. set_hide_title(True) subtracts 30 from height.
    # Formula: (50 if hide_title else 70) so that after set_hide_title's -30
    # the hide_title=True case ends up with content_h + 20 bottom pad as well.
    card_height = content_h + (50 if hide_title else 70)

    card = Card(
        width=card_width,
        height=card_height,
        border_radius=border_radius,
        colors=colors,
        custom_title=custom_title,
        default_title="Most Used Languages",
    )
    if hide_border:
        card.set_hide_border(True)
    if hide_title:
        card.set_hide_title(True)
    if disable_animations:
        card.disable_animations()

    return card.render(body)
