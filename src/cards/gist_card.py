"""
gist_card.py -- Renders a GitHub Gist SVG card.

Similar shape to the repo card but for a gist: title = gist file name,
optional owner prefix, description, language dot, stars, forks.

Import convention: deployment root is src/; siblings imported without src. prefix.
"""

from __future__ import annotations

from cards.base_card import Card
from common.colors import get_card_colors
from common.icons import ICONS
from common.render_utils import encode_html, k_formatter, wrap_text_multiline

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CARD_WIDTH = 400
_ICON_SIZE = 16


def _lang_dot(color: str | None) -> str:
    c = color if color else "#858585"
    return f'<circle cx="0" cy="-5" r="6" fill="{c}"/>'


def _icon_text(icon_svg: str, label: str, text_color: str, x: float = 0.0) -> str:
    return (
        f'<g transform="translate({x:.1f}, 0)">'
        f'<svg x="0" y="-13" width="{_ICON_SIZE}" height="{_ICON_SIZE}" '
        f'viewBox="0 0 16 16" fill="{text_color}">'
        f'{icon_svg}'
        f'</svg>'
        f'<text x="{_ICON_SIZE + 4}" y="0" fill="{text_color}" '
        f'font-size="12" font-family="Segoe UI,Ubuntu,sans-serif">'
        f'{encode_html(label)}'
        f'</text>'
        f'</g>'
    )


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_gist_card(gist: dict, options: dict | None = None) -> str:
    """
    Render a Gist card SVG.

    Parameters
    ----------
    gist:
        Dict with keys: name, nameWithOwner, description,
        language (str or None), starsCount, forksCount, ownerLogin.
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

    # Title: gist file name, optionally prefixed with owner
    gist_name: str = gist.get("name", "")
    owner: str = gist.get("ownerLogin", "")
    if show_owner and owner:
        title = f"{owner}/{gist_name}"
    else:
        title = gist_name

    # Description (up to 2 lines)
    raw_desc: str = gist.get("description") or ""
    desc_lines = wrap_text_multiline(raw_desc, width=55, max_lines=2) if raw_desc else []

    # Language (gist has a single language string, not an object)
    lang_name: str = gist.get("language") or ""
    lang_color: str | None = None  # Gist API does not provide a language color

    star_count: int = gist.get("starsCount", 0)
    fork_count: int = gist.get("forksCount", 0)

    # ---------- Build body SVG ----------
    parts: list[str] = []
    y = 0

    # Gist icon + title
    gist_icon_svg = ICONS.get("gists", ICONS.get("repos", ""))
    parts.append(
        f'<svg x="0" y="{y}" width="{_ICON_SIZE}" height="{_ICON_SIZE}" '
        f'viewBox="0 0 16 16" fill="{icon_color}">'
        f'{gist_icon_svg}'
        f'</svg>'
        f'<text x="{_ICON_SIZE + 6}" y="{y + 12}" fill="{title_color}" '
        f'font-size="13" font-weight="bold" font-family="Segoe UI,Ubuntu,sans-serif">'
        f'{encode_html(title)}'
        f'</text>'
    )
    y += 22

    # Description
    for line in desc_lines:
        parts.append(
            f'<text x="0" y="{y}" fill="{text_color}" font-size="11" '
            f'font-family="Segoe UI,Ubuntu,sans-serif">{encode_html(line)}</text>'
        )
        y += 16

    # Footer row: language dot, stars, forks
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
    footer_parts.append(_icon_text(star_svg, star_label, text_color, x=footer_x))
    footer_x += len(star_label) * 7 + 28

    fork_svg = ICONS.get("repos", "")
    fork_label = k_formatter(fork_count)
    footer_parts.append(_icon_text(fork_svg, fork_label, text_color, x=footer_x))

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
    # Title is rendered inline in the body; suppress card chrome title
    card.set_hide_title(True)
    if hide_border:
        card.set_hide_border(True)

    body = f'<g transform="translate(20, 20)">{"".join(parts)}</g>'
    return card.render(body)
