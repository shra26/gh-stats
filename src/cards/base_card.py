"""
cards/base_card.py -- shared SVG card chrome.

Provides the Card class that mirrors the behaviour of Card.js in the original
github-readme-stats project: border, title, gradient background, animation
keyframes, and accessibility labels.

Import convention: deployment root is src/; siblings imported without src. prefix.
"""

from __future__ import annotations

from common.render_utils import encode_html


class Card:
    """
    Construct and render a themed SVG card.

    Parameters
    ----------
    width : int
        SVG viewport width in pixels.
    height : int
        SVG viewport height in pixels.
    border_radius : float
        Corner radius for the background rect, in pixels.
    colors : dict | None
        Dict returned by get_card_colors(): titleColor, textColor, iconColor,
        bgColor (str or list[str] for gradient), borderColor, ringColor.
        When None, all color attributes default to empty strings (useful only
        in tests that supply a fully custom body).
    custom_title : str | None
        Overrides default_title when provided.
    default_title : str
        Fallback title text when custom_title is not given.
    title_prefix_icon : str | None
        Raw inner SVG markup for a 16x16 icon rendered before the title text.
    """

    def __init__(
        self,
        *,
        width: int = 100,
        height: int = 100,
        border_radius: float = 4.5,
        colors: dict | None = None,
        custom_title: str | None = None,
        default_title: str = "",
        title_prefix_icon: str | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.border_radius = border_radius
        self.colors: dict = colors if colors is not None else {}

        self._title_text: str = custom_title if custom_title is not None else default_title
        self.title_prefix_icon: str | None = title_prefix_icon

        # Layout constants (matching Card.js)
        self.padding_x: int = 25
        self.padding_y: int = 35

        # Feature flags
        self.animations: bool = True
        self.hide_border: bool = False
        self.hide_title: bool = False

        # Custom stylesheet injected before keyframes
        self._css: str = ""

        # Accessibility
        self._a11y_title: str = ""
        self._a11y_desc: str = ""

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def disable_animations(self) -> None:
        """Turn off all CSS animations on this card."""
        self.animations = False

    def set_hide_border(self, value: bool) -> None:
        """Control whether the border stroke is visible."""
        self.hide_border = value

    def set_hide_title(self, value: bool) -> None:
        """
        Control whether the title row is rendered.

        When hiding the title, reduce the card height by 30 px to reclaim
        the space that would have been occupied by the title row.
        """
        if value and not self.hide_title:
            self.height = max(0, self.height - 30)
        elif not value and self.hide_title:
            self.height += 30
        self.hide_title = value

    def set_css(self, value: str) -> None:
        """Inject additional CSS into the <style> block."""
        self._css = value

    def set_title(self, text: str) -> None:
        """Override the rendered title text."""
        self._title_text = text

    def set_accessibility_label(self, *, title: str, desc: str) -> None:
        """Set the <title> and <desc> accessibility elements."""
        self._a11y_title = title
        self._a11y_desc = desc

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def render_gradient(self) -> str:
        """
        Emit a <defs> block containing a linearGradient when bgColor is a list.

        The list format is [angle, color1, color2, ...] where angle is the
        rotation in degrees and each color is a bare hex string (no '#').
        Returns an empty string when bgColor is a plain color string.
        """
        bg = self.colors.get("bgColor", "")
        if not isinstance(bg, list):
            return ""

        # bg = [angle, c1, c2, ...]
        angle = bg[0]
        color_stops = bg[1:]
        n = len(color_stops)

        stops: list[str] = []
        for i, hex_color in enumerate(color_stops):
            offset = 0 if n == 1 else round(i * 100 / (n - 1))
            # Colors stored without '#'; prepend it
            color_val = f"#{hex_color}" if not hex_color.startswith("#") else hex_color
            stops.append(
                f'      <stop offset="{offset}%" stop-color="{color_val}" />'
            )

        stops_str = "\n".join(stops)
        return (
            "  <defs>\n"
            f'    <linearGradient id="gradient" gradientTransform="rotate({angle})"'
            ' gradientUnits="userSpaceOnUse">\n'
            f"{stops_str}\n"
            "    </linearGradient>\n"
            "  </defs>"
        )

    def render_title(self) -> str:
        """
        Render the card title row.

        Includes an optional prefix icon (16x16 viewBox) and the title text
        in the titleColor from the colors dict.
        """
        if self.hide_title:
            return ""

        title_color = self.colors.get("titleColor", "#000000")
        safe_title = encode_html(self._title_text)

        if self.title_prefix_icon:
            # Icon sits at x=0; title text offset by icon width (25) + gap (5)
            icon_part = (
                f'    <svg data-testid="card-title-icon" x="0" y="-13" '
                f'width="16" height="16" viewBox="0 0 16 16" fill="{title_color}">\n'
                f"      {self.title_prefix_icon}\n"
                f"    </svg>"
            )
            text_x = 25
        else:
            icon_part = ""
            text_x = 0

        text_part = (
            f'    <text x="{text_x}" y="0" class="header" '
            f'data-testid="card-title" '
            f'fill="{title_color}" '
            f'font-size="18" '
            f'font-weight="600" '
            f'font-family="Segoe UI, Ubuntu, Sans-Serif">'
            f"{safe_title}</text>"
        )

        return (
            f'  <g data-testid="card-title" transform="translate({self.padding_x}, {self.padding_y})">\n'
            f"{icon_part}\n"
            f"{text_part}\n"
            f"  </g>"
        )

    def get_animations(self) -> str:
        """
        Return shared CSS @keyframes used by all cards.

        Returns an empty string when animations are disabled so callers can
        embed this directly into the <style> block without an extra branch.
        """
        if not self.animations:
            return ""

        return """
    @keyframes scaleInAnimation {
      from { transform: translate(-5px, 5px) scale(0); opacity: 0; }
      to   { transform: translate(-5px, 5px) scale(1); opacity: 1; }
    }
    @keyframes fadeInAnimation {
      from { opacity: 0; }
      to   { opacity: 1; }
    }"""

    def render(self, body: str) -> str:
        """
        Assemble the full SVG document for this card.

        Parameters
        ----------
        body : str
            Inner SVG markup to embed inside the card body area (below the
            title, offset by padding and title height).

        Returns
        -------
        str
            A complete SVG document as a string.
        """
        bg = self.colors.get("bgColor", "#fffefe")
        border_color = self.colors.get("borderColor", "#e4e2e2")

        # Background fill: gradient reference or plain color
        if isinstance(bg, list):
            fill = "url(#gradient)"
        else:
            fill = bg

        border_opacity = "0" if self.hide_border else "1"

        # Animation-disable override: inject a rule that kills all durations
        if not self.animations:
            anim_override = (
                "\n    * { animation-duration: 0s !important;"
                " animation-delay: 0s !important; }"
            )
        else:
            anim_override = ""

        style_content = f"{self._css}{self.get_animations()}{anim_override}"

        # Accessibility elements
        a11y_parts: list[str] = []
        if self._a11y_title:
            a11y_parts.append(
                f'  <title id="card-title">{encode_html(self._a11y_title)}</title>'
            )
        if self._a11y_desc:
            a11y_parts.append(
                f'  <desc id="card-desc">{encode_html(self._a11y_desc)}</desc>'
            )
        a11y_str = "\n".join(a11y_parts)

        # Gradient defs block
        gradient_defs = self.render_gradient()

        # Background rect
        bg_rect = (
            f'  <rect data-testid="card-bg" '
            f'x="0.5" y="0.5" rx="{self.border_radius}" '
            f'height="99%" width="{self.width - 1}" '
            f'stroke="{border_color}" '
            f'fill="{fill}" '
            f'stroke-opacity="{border_opacity}" />'
        )

        # Title group
        title_group = self.render_title()

        # Body is offset below the title row
        # When hide_title is False, the title occupies ~50px (padding_y + title height)
        title_height = 0 if self.hide_title else 50
        body_offset_x = self.padding_x
        body_offset_y = title_height

        body_group = (
            f'  <g data-testid="main-card-body" '
            f'transform="translate({body_offset_x}, {body_offset_y})">\n'
            f"{body}\n"
            f"  </g>"
        )

        # Aria attributes on root element
        aria_attrs = ""
        if self._a11y_title:
            aria_attrs += ' aria-labelledby="card-title"'
        if self._a11y_desc:
            aria_attrs += ' aria-describedby="card-desc"'
        if self._a11y_title or self._a11y_desc:
            aria_attrs += ' role="img"'

        parts: list[str] = [
            f'<svg width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}" '
            f'fill="none" '
            f'xmlns="http://www.w3.org/2000/svg"'
            f'{aria_attrs}>',
        ]

        if a11y_str:
            parts.append(a11y_str)

        if style_content.strip():
            parts.append(f"  <style>\n{style_content}\n  </style>")

        if gradient_defs:
            parts.append(gradient_defs)

        parts.append(bg_rect)

        if not self.hide_title:
            parts.append(title_group)

        parts.append(body_group)
        parts.append("</svg>")

        return "\n".join(parts)
