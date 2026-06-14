"""
cards/stats_card.py -- GitHub stats SVG card renderer.

Entry point: render_stats_card(stats, options) -> str (SVG).

Import convention: deployment root is src/; siblings imported without src. prefix.
"""

from __future__ import annotations

import math
from typing import Any

from cards.base_card import Card
from common.colors import get_card_colors
from common.icons import ICONS
from common.render_utils import clamp, encode_html, format_number
from config import (
    RANK_CARD_DEFAULT_WIDTH,
    RANK_CARD_MIN_WIDTH,
    RANK_ONLY_CARD_DEFAULT_WIDTH,
    RANK_ONLY_CARD_MIN_WIDTH,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _icon_svg(name: str, color: str, size: int = 16) -> str:
    """Wrap an ICONS inner-markup snippet in a sized <svg> element."""
    inner = ICONS.get(name, "")
    return (
        f'<svg data-testid="icon-{name}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}" '
        f'fill="{color}">'
        f"{inner}"
        f"</svg>"
    )


def _circ(v: float) -> float:
    """
    Map a progress value (0-100) to a stroke-dashoffset for the rank ring.

    circ(v) = ((100 - v) / 100) * (pi * 80)
    The ring has r=40, so circumference = 2*pi*40 = pi*80 ~= 251.
    """
    return ((100.0 - v) / 100.0) * (math.pi * 80)


# ---------------------------------------------------------------------------
# Stat-row builder
# ---------------------------------------------------------------------------

def _build_stat_rows(
    stats: dict[str, Any],
    options: dict[str, Any],
    icon_color: str,
    text_color: str,
) -> tuple[list[str], int]:
    """
    Build SVG markup for each stat row.

    Returns (rows, count) where rows is a list of raw SVG strings and count
    is the number of rows rendered (used for height calculation).

    Each row carries a stagger animation-delay based on its ordinal index.
    The delay formula is: (index + 3) * 150 ms, matching the original JS.
    """
    hide: set[str] = set(options.get("hide", []) or [])
    show: set[str] = set(options.get("show", []) or [])
    show_icons: bool = bool(options.get("show_icons", False))
    number_format: str = options.get("number_format", "short") or "short"
    number_precision: int = int(options.get("number_precision", 1) or 1)
    include_all_commits: bool = bool(options.get("include_all_commits", False))
    commits_year: int | None = options.get("commits_year")
    text_bold: bool = options.get("text_bold", True)
    if text_bold is None:
        text_bold = True

    font_weight = "700" if text_bold else "400"

    def _fmt(val: float) -> str:
        return format_number(val, number_format, number_precision)

    # -- Standard stat definitions (order matters) --
    # Each entry: (stat_key_in_hide, icon_key, label_fn, value_fn)
    # label_fn and value_fn accept the stats dict.
    standard: list[tuple[str, str, str, Any]] = []

    if "stars" not in hide:
        standard.append(("stars", "star", "Total Stars Earned", stats.get("totalStars", 0)))

    if "commits" not in hide:
        if include_all_commits:
            commits_label = "Total Commits"
        elif commits_year:
            commits_label = f"Total Commits ({commits_year})"
        else:
            commits_label = "Total Commits (this year)"
        standard.append(("commits", "commits", commits_label, stats.get("totalCommits", 0)))

    if "prs" not in hide:
        standard.append(("prs", "prs", "Total PRs", stats.get("totalPRs", 0)))

    if "issues" not in hide:
        standard.append(("issues", "issues", "Total Issues", stats.get("totalIssues", 0)))

    if "contribs" not in hide:
        standard.append(("contribs", "contribs", "Contributed to (last year)", stats.get("contributedTo", 0)))

    # -- Optional extras from `show` --
    extra: list[tuple[str, str, str, Any]] = []

    if "reviews" in show:
        extra.append(("reviews", "review", "Total Reviews", stats.get("totalReviews", 0)))

    if "prs_merged" in show:
        extra.append(("prs_merged", "prs_merged", "Total PRs Merged", stats.get("totalPRsMerged", 0)))

    if "prs_merged_percentage" in show:
        raw_pct = stats.get("mergedPRsPercentage", 0.0)
        pct_str = f"{raw_pct:.1f}%"
        extra.append(("prs_merged_percentage", "prs_merged", "Merged PRs Percentage", pct_str))

    if "discussions_started" in show:
        extra.append(("discussions_started", "discussions", "Total Discussions Started", stats.get("totalDiscussionsStarted", 0)))

    if "discussions_answered" in show:
        extra.append(("discussions_answered", "discussions", "Total Discussions Answered", stats.get("totalDiscussionsAnswered", 0)))

    all_rows = standard + extra
    rows: list[str] = []

    for idx, (_, icon_key, label, value) in enumerate(all_rows):
        delay_ms = (idx + 3) * 150

        # Format value unless it's already a string (e.g. prs_merged_percentage)
        if isinstance(value, str):
            value_str = value
        else:
            value_str = _fmt(float(value))

        # Icon element (only when show_icons is True)
        if show_icons:
            icon_el = (
                f'<g class="stagger" style="animation-delay: {delay_ms}ms"'
                f' transform="translate(0, 0)">'
                f'{_icon_svg(icon_key, icon_color)}'
                f'</g>'
            )
            label_x = 25
        else:
            icon_el = ""
            label_x = 0

        # Label text
        safe_label = encode_html(label)
        label_el = (
            f'<text class="stat bold" '
            f'x="{label_x}" '
            f'y="0" '
            f'fill="{text_color}" '
            f'font-size="13" '
            f'font-family="Segoe UI, Ubuntu, Sans-Serif">'
            f"{safe_label}"
            f"</text>"
        )

        # Value text (right-aligned within the stat area)
        value_el = (
            f'<text class="stat bold" '
            f'x="200" '
            f'y="0" '
            f'text-anchor="middle" '
            f'fill="{text_color}" '
            f'font-size="13" '
            f'font-weight="{font_weight}" '
            f'font-family="Segoe UI, Ubuntu, Sans-Serif">'
            f"{encode_html(value_str)}"
            f"</text>"
        )

        row_svg = (
            f'<g class="stagger" '
            f'style="animation-delay: {delay_ms}ms" '
            f'transform="translate(0, {idx * 25})">'
            f"\n  {icon_el}"
            f"\n  {label_el}"
            f"\n  {value_el}"
            f"\n</g>"
        )
        rows.append(row_svg)

    return rows, len(rows)


# ---------------------------------------------------------------------------
# Rank ring
# ---------------------------------------------------------------------------

def _build_rank_ring(
    rank: dict[str, Any],
    ring_color: str,
    rank_icon: str = "default",
) -> str:
    """
    Build the animated rank ring SVG group.

    The ring is composed of:
    - A static rim circle (opacity 0.2) for the track.
    - An animated arc circle (opacity 0.8) that fills in proportionally to rank.

    The @keyframes block is embedded inline because it references a specific
    percentile value and cannot be shared across cards.
    """
    level: str = rank.get("level", "C")
    percentile: float = float(rank.get("percentile", 100.0))

    progress: float = 100.0 - percentile
    dash_start: float = _circ(0)
    dash_end: float = _circ(progress)

    # Circumference for stroke-dasharray
    circumference: float = math.pi * 80  # 2*pi*r where r=40, simplified

    keyframes = (
        f"@keyframes rankAnimation {{\n"
        f"  from {{ stroke-dashoffset: {dash_start:.4f}; }}\n"
        f"  to   {{ stroke-dashoffset: {dash_end:.4f}; }}\n"
        f"}}"
    )

    # Center label inside the ring
    safe_level = encode_html(level)

    if rank_icon == "percentile":
        # Show numeric percentile instead of the letter grade
        pct_str = f"{percentile:.1f}%"
        center_text = (
            f'<text '
            f'x="-10" y="13" '
            f'text-anchor="middle" '
            f'fill="{ring_color}" '
            f'font-size="14" '
            f'font-weight="700" '
            f'font-family="Segoe UI, Ubuntu, Sans-Serif">'
            f"{encode_html(pct_str)}"
            f"</text>"
        )
    elif rank_icon == "github":
        # GitHub octocat icon inside the ring (small, centered)
        github_inner = ICONS.get("github", "")
        center_text = (
            f'<svg x="-18" y="-5" width="16" height="16" '
            f'viewBox="0 0 16 16" fill="{ring_color}">'
            f"{github_inner}"
            f"</svg>\n"
            f'<text '
            f'x="-10" y="18" '
            f'text-anchor="middle" '
            f'fill="{ring_color}" '
            f'font-size="11" '
            f'font-weight="700" '
            f'font-family="Segoe UI, Ubuntu, Sans-Serif">'
            f"{safe_level}"
            f"</text>"
        )
    else:
        # Default: rank letter grade
        center_text = (
            f'<text '
            f'x="-10" y="13" '
            f'text-anchor="middle" '
            f'fill="{ring_color}" '
            f'font-size="22" '
            f'font-weight="700" '
            f'font-family="Segoe UI, Ubuntu, Sans-Serif">'
            f"{safe_level}"
            f"</text>"
        )

    ring_svg = (
        f"<style>\n{keyframes}\n</style>\n"
        f'<circle class="rank-circle-rim" '
        f'cx="-10" cy="8" r="40" '
        f'fill="none" '
        f'stroke="{ring_color}" '
        f'stroke-opacity="0.2" '
        f'stroke-width="6" />\n'
        f'<circle class="rank-circle" '
        f'cx="-10" cy="8" r="40" '
        f'fill="none" '
        f'stroke="{ring_color}" '
        f'stroke-opacity="0.8" '
        f'stroke-width="6" '
        f'stroke-linecap="round" '
        f'stroke-dasharray="{circumference:.4f}" '
        f'stroke-dashoffset="{dash_start:.4f}" '
        f'style="'
        f"transform: rotate(-90deg); "
        f"transform-origin: -10px 8px; "
        f'animation: rankAnimation 1s forwards ease-in-out;" />\n'
        f"{center_text}"
    )

    return ring_svg


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_stats_card(
    stats: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> str:
    """
    Render a GitHub stats SVG card.

    Parameters
    ----------
    stats : dict
        Dict produced by stats_fetcher.fetch_stats(). Expected keys:
        name, username, totalStars, totalCommits, totalPRs, totalPRsMerged,
        mergedPRsPercentage, totalReviews, totalIssues, totalDiscussionsStarted,
        totalDiscussionsAnswered, contributedTo, followers,
        rank (dict with keys level and percentile).
    options : dict | None
        Parsed query parameters. All keys are optional. Recognised keys:
        hide, show, hide_title, hide_rank, hide_border, show_icons, card_width,
        line_height, title_color, ring_color, icon_color, text_color, text_bold,
        bg_color, theme, custom_title, locale, disable_animations, border_radius,
        number_format, number_precision, rank_icon, include_all_commits, commits_year.

    Returns
    -------
    str
        A complete SVG document string.
    """
    opts: dict[str, Any] = options or {}

    # -- Resolve booleans and scalars -----------------------------------------
    hide_title: bool = bool(opts.get("hide_title", False))
    hide_rank: bool = bool(opts.get("hide_rank", False))
    hide_border: bool = bool(opts.get("hide_border", False))
    show_icons: bool = bool(opts.get("show_icons", False))
    disable_animations: bool = bool(opts.get("disable_animations", False))
    line_height: int = int(opts.get("line_height", 25) or 25)
    border_radius: float = float(opts.get("border_radius", 4.5) or 4.5)
    number_format: str = opts.get("number_format", "short") or "short"
    number_precision: int = int(opts.get("number_precision", 1) or 1)
    rank_icon: str = opts.get("rank_icon", "default") or "default"
    custom_title: str | None = opts.get("custom_title")

    # -- Colors ---------------------------------------------------------------
    colors: dict = get_card_colors(
        title_color=opts.get("title_color"),
        text_color=opts.get("text_color"),
        icon_color=opts.get("icon_color"),
        bg_color=opts.get("bg_color"),
        border_color=opts.get("border_color"),
        ring_color=opts.get("ring_color"),
        theme=opts.get("theme"),
    )

    # -- Card width -----------------------------------------------------------
    # hide_rank -> use RANK_ONLY constants? No: per the plan, hide_rank means
    # stats-only. We always use RANK_CARD_DEFAULT_WIDTH as base and clamp down
    # to RANK_CARD_MIN_WIDTH (unless user supplied a narrower override, in which
    # case still enforce the minimum).
    raw_width: int | None = opts.get("card_width")
    if hide_rank:
        # Without the ring we can use the rank-only width constants as base
        default_w = RANK_ONLY_CARD_DEFAULT_WIDTH
        min_w = RANK_ONLY_CARD_MIN_WIDTH
    else:
        default_w = RANK_CARD_DEFAULT_WIDTH
        min_w = RANK_CARD_MIN_WIDTH

    if raw_width is not None:
        card_width = clamp(int(raw_width), min_w, 1000)
    else:
        card_width = default_w

    # -- Build stat rows ------------------------------------------------------
    icon_color: str = colors["iconColor"]
    text_color: str = colors["textColor"]

    stat_rows, row_count = _build_stat_rows(stats, opts, icon_color, text_color)

    # -- Card height ----------------------------------------------------------
    # Match the original JS heuristic:
    #   base 45px + rows * line_height + title area (50px when shown).
    title_height = 0 if hide_title else 50
    card_height = max(45 + (row_count * line_height) + title_height, 150)

    # -- Rank ring position (right side of card) ------------------------------
    ring_x = card_width - 90  # leaves ~90px margin on the right
    ring_y = (card_height // 2) - 20

    # -- Assemble body SVG ----------------------------------------------------
    # Stats group on the left
    stats_group_parts: list[str] = []
    for row in stat_rows:
        stats_group_parts.append(row)

    stats_group = (
        f'<g data-testid="stat-items" '
        f'transform="translate(0, 0)">\n'
        + "\n".join(stats_group_parts)
        + "\n</g>"
    )

    # Rank ring on the right (unless hidden)
    if hide_rank:
        rank_group = ""
    else:
        rank_data = stats.get("rank", {"level": "C", "percentile": 100.0})
        ring_svg = _build_rank_ring(rank_data, colors["ringColor"], rank_icon)
        rank_group = (
            f'<g data-testid="rank-circle" '
            f'transform="translate({ring_x}, {ring_y})">\n'
            f"{ring_svg}\n"
            f"</g>"
        )

    body = stats_group
    if rank_group:
        body = body + "\n" + rank_group

    # -- Build and configure Card ---------------------------------------------
    name: str = stats.get("name", stats.get("username", ""))
    default_title = f"{encode_html(name)}'s GitHub Stats"

    card = Card(
        width=card_width,
        height=card_height,
        border_radius=border_radius,
        colors=colors,
        custom_title=custom_title,
        default_title=default_title,
    )

    card.set_hide_border(hide_border)
    if hide_title:
        card.set_hide_title(True)
    if disable_animations:
        card.disable_animations()

    # Accessibility labels
    rank_data = stats.get("rank", {"level": "C", "percentile": 100.0})
    a11y_title = f"{name}'s GitHub Stats"
    a11y_desc = (
        f"Total Stars Earned: {stats.get('totalStars', 0)}, "
        f"Total Commits: {stats.get('totalCommits', 0)}, "
        f"Total PRs: {stats.get('totalPRs', 0)}, "
        f"Total Issues: {stats.get('totalIssues', 0)}, "
        f"Contributed to (last year): {stats.get('contributedTo', 0)}, "
        f"Rank: {rank_data.get('level', 'C')}"
    )
    card.set_accessibility_label(title=a11y_title, desc=a11y_desc)

    return card.render(body)
