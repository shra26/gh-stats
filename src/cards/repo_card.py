"""
repo_card.py -- Renders the Repository (pin) SVG card.

Import convention: deployment root is src/; siblings imported without src. prefix.
"""

from __future__ import annotations

from cards.base_card import Card
from common.colors import get_card_colors
from common.icons import ICONS
from common.render_utils import encode_html, k_formatter, wrap_text_multiline, clamp

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CARD_WIDTH = 400
_CARD_HEIGHT = 120
_REPO_ICON_SIZE = 16
_FOOTER_Y = 100  # y position of the footer row within the body group


def _lang_dot(color: str | None) -> str:
    c = color if color else "#858585"
    return (
        f'<circle cx="0" cy="-5" r="6" fill="{c}"/>'
    )


def _icon_text(icon_svg: str, label: str, text_color: str, x: float = 0) -> str:
    """Render an inline icon followed by a text label in a <g>."""
    return (
        f'<g transform="translate({x:.1f}, 0)">'
        f'<svg x="0" y="-13" width="{_REPO_ICON_SIZE}" height="{_REPO_ICON_SIZE}" '
        f'viewBox="0 0 16 16" fill="{text_color}">'
        f'{icon_svg}'
        f'</svg>'
        f'<text x="{_REPO_ICON_SIZE + 4}" y="0" fill="{text_color}" '
        f'font-size="12" font-family="Segoe UI,Ubuntu,sans-serif">'
        f'{encode_html(label)}'
        f'</text>'
        f'</g>'
    )


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_repo_card(repo: dict, options: dict | None = None) -> str:
    """
    Render a Repository card SVG.

    Parameters
    ----------
    repo:
        Dict with keys: name, nameWithOwner, description,
        primaryLanguage ({color, name} or None), starCount, forkCount,
        isArchived, isTemplate.
    options:
        Raw query-param dict.

    Returns
    -------
    str
        Complete SVG markup.
    """
    opts: dict = options or {}

    hide_border: bool = str(opts.get("hide_border", "false")).lower() == "true"
    show_owner: bool = str(opts.get("show_owner", "false")).lower() == "true"
    try:
        border_radius = float(opts.get("border_radius", 4.5))
    except (TypeError, ValueError):
        border_radius = 4.5
    try:
        desc_lines = clamp(int(opts.get("description_lines_count", 2)), 1, 3)
    except (TypeError, ValueError):
        desc_lines = 2

    colors = get_card_colors(
        title_color=opts.get("title_color"),
        icon_color=opts.get("icon_color"),
        text_color=opts.get("text_color"),
        bg_color=opts.get("bg_color"),
        border_color=opts.get("border_color"),
        theme=opts.get("theme"),
    )
    text_color = colors["textColor"]
    icon_color = colors["iconColor"]
    title_color = colors["titleColor"]

    # Title
    repo_name: str = repo.get("name", "")
    name_with_owner: str = repo.get("nameWithOwner", "")
    if show_owner and name_with_owner:
        title = name_with_owner
    else:
        title = repo_name

    # Badges
    badges: list[str] = []
    if repo.get("isArchived"):
        badges.append("Archived")
    if repo.get("isTemplate"):
        badges.append("Template")

    # Description
    raw_desc: str = repo.get("description") or ""
    desc_lines_list = wrap_text_multiline(raw_desc, width=55, max_lines=desc_lines) if raw_desc else []

    # Primary language
    primary_lang: dict | None = repo.get("primaryLanguage")
    lang_name: str = primary_lang.get("name", "") if primary_lang else ""
    lang_color: str | None = primary_lang.get("color") if primary_lang else None

    star_count: int = repo.get("starCount", 0)
    fork_count: int = repo.get("forkCount", 0)

    # ---------- Build body SVG ----------
    parts: list[str] = []
    y = 0

    # Repo icon + title in header
    repo_icon_svg = ICONS.get("repos", "")
    parts.append(
        f'<svg x="0" y="{y}" width="{_REPO_ICON_SIZE}" height="{_REPO_ICON_SIZE}" '
        f'viewBox="0 0 16 16" fill="{icon_color}">'
        f'{repo_icon_svg}'
        f'</svg>'
        f'<text x="{_REPO_ICON_SIZE + 6}" y="{y + 12}" fill="{title_color}" '
        f'font-size="13" font-weight="bold" font-family="Segoe UI,Ubuntu,sans-serif">'
        f'{encode_html(title)}'
        f'</text>'
    )

    # Badges (Archived / Template)
    badge_x = _REPO_ICON_SIZE + 8 + len(title) * 7.5
    for badge in badges:
        parts.append(
            f'<g transform="translate({badge_x:.0f}, {y})">'
            f'<rect x="0" y="0" rx="2" ry="2" width="{len(badge) * 6 + 8}" height="14" '
            f'fill="none" stroke="{text_color}" stroke-opacity="0.4" stroke-width="1"/>'
            f'<text x="4" y="10" fill="{text_color}" font-size="9" '
            f'font-family="Segoe UI,Ubuntu,sans-serif">{encode_html(badge)}</text>'
            f'</g>'
        )
        badge_x += len(badge) * 6 + 14

    y += 22

    # Description lines
    for line in desc_lines_list:
        parts.append(
            f'<text x="0" y="{y}" fill="{text_color}" font-size="11" '
            f'font-family="Segoe UI,Ubuntu,sans-serif">{encode_html(line)}</text>'
        )
        y += 16

    # Footer: language dot, stars, forks
    footer_y = max(y + 10, 70)
    footer_parts: list[str] = []
    footer_x = 0.0

    if lang_name:
        dot_svg = _lang_dot(lang_color)
        footer_parts.append(
            f'<g transform="translate({footer_x:.1f}, 0)">'
            f'{dot_svg}'
            f'<text x="14" y="0" fill="{text_color}" font-size="11" '
            f'font-family="Segoe UI,Ubuntu,sans-serif">{encode_html(lang_name)}</text>'
            f'</g>'
        )
        footer_x += len(lang_name) * 7 + 24

    star_svg = ICONS.get("star", "")
    star_label = k_formatter(star_count)
    parts_star = _icon_text(star_svg, star_label, text_color, x=footer_x)
    footer_parts.append(parts_star)
    footer_x += len(star_label) * 7 + 28

    fork_svg = ICONS.get("repos", "")
    fork_label = k_formatter(fork_count)
    parts_fork = _icon_text(fork_svg, fork_label, text_color, x=footer_x)
    footer_parts.append(parts_fork)

    parts.append(
        f'<g transform="translate(0, {footer_y})">'
        + "".join(footer_parts)
        + "</g>"
    )

    card_height = footer_y + 24

    card = Card(
        width=_CARD_WIDTH,
        height=card_height,
        border_radius=border_radius,
        colors=colors,
        custom_title=None,
        default_title=title,
    )
    # Repo card renders its own title inline in the body; suppress the card chrome title
    card.set_hide_title(True)
    if hide_border:
        card.set_hide_border(True)

    body = f'<g transform="translate(20, 20)">{"".join(parts)}</g>'
    return card.render(body)
