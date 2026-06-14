"""
render_error.py -- error-card SVG renderer.

Returns a self-contained SVG with HTTP 200 so GitHub Camo never shows a
broken-image icon in the README.  No external theme dependency.

Import convention: deployment root is src/; siblings imported without src. prefix.
"""

from __future__ import annotations

from common.render_utils import encode_html


# Card dimensions (match github-readme-stats error card)
_WIDTH: float = 576.5
_HEIGHT: float = 120

# Colors -- static, no theme needed
_BG_COLOR = "#fffefe"
_BORDER_COLOR = "#e4e2e2"
_TITLE_COLOR = "#2f80ed"
_TEXT_COLOR = "#434d58"
_SECONDARY_COLOR = "#6a737d"


def render_error(message: str, secondary_message: str = "") -> str:
    """
    Render a standalone error-card SVG.

    Parameters
    ----------
    message:
        Primary error description.  HTML-escaped before embedding.
    secondary_message:
        Optional supplementary detail line shown in a lighter color.

    Returns
    -------
    A complete SVG string (width 576.5, height 120) safe to return as
    ``image/svg+xml`` with HTTP 200.
    """
    safe_message = encode_html(message)
    safe_secondary = encode_html(secondary_message) if secondary_message else ""

    secondary_element = ""
    if safe_secondary:
        secondary_element = (
            f'<text x="25" y="90" font-family="Segoe UI,Helvetica,Arial,sans-serif" '
            f'font-size="12" fill="{_SECONDARY_COLOR}">'
            f"{safe_secondary}"
            f"</text>"
        )

    svg = (
        f'<svg width="{_WIDTH}" height="{_HEIGHT}" '
        f'viewBox="0 0 {_WIDTH} {_HEIGHT}" '
        f'xmlns="http://www.w3.org/2000/svg">\n'
        # Background rect
        f'  <rect x="0.5" y="0.5" rx="4.5" '
        f'height="{_HEIGHT - 1}" stroke="{_BORDER_COLOR}" '
        f'width="{_WIDTH - 1}" fill="{_BG_COLOR}" stroke-opacity="1"/>\n'
        # Title: "Something went wrong!"
        f'  <text x="25" y="45" '
        f'font-family="Segoe UI,Helvetica,Arial,sans-serif" '
        f'font-weight="bold" font-size="15" fill="{_TITLE_COLOR}">'
        f"Something went wrong! file an issue at "
        f'<tspan fill="{_TITLE_COLOR}" text-decoration="underline">'
        f"git.io/JnNSY"
        f"</tspan>"
        f"</text>\n"
        # Primary message
        f'  <text x="25" y="70" '
        f'font-family="Segoe UI,Helvetica,Arial,sans-serif" '
        f'font-size="13" fill="{_TEXT_COLOR}">'
        f"{safe_message}"
        f"</text>\n"
        # Optional secondary message
        f"  {secondary_element}\n"
        f"</svg>"
    )

    return svg
