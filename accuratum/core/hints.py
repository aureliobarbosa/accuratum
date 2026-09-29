"""Render-side knobs — separate from :class:`SundialSpec` to keep specs portable.

``RenderHints`` carries how a plot is drawn: overlay images, figure size,
fonts, colors. A project saves them next to the spec (in
``project.json``'s ``render`` section) but outside ``spec_hash``, so changing
them never invalidates the computed geometry. Renderers take ``(plot, hints)``.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Overlay:
    """An image drawn over the figure; ``rect`` is in figure coords (0-1).

    ``name`` (e.g. ``"logo"``) lets the CLI replace one overlay of a saved
    project by flag.
    """

    image_path: str
    rect: tuple[float, float, float, float]
    name: str = ""


@dataclass
class RenderHints:
    """``axes_rect`` (figure coords) holds the drawing, pinned to its top edge.
    The band above it is the header, where the default overlays sit; the
    drawing's shape changes with latitude and period, so overlays placed on
    top of it would cover lines somewhere.

    The plot's title and subtitle go in the header too, between the default
    overlays, at ``title_xy`` and ``subtitle_xy``."""

    overlays: list[Overlay] = field(default_factory=list)
    figsize: tuple[float, float] = (8.0, 6.0)
    axes_rect: tuple[float, float, float, float] = (0.07, 0.05, 0.9, 0.75)
    line_color: str = "green"
    line_width: float = 0.5
    label_color: str = "black"
    label_fontsize: float = 7.0
    title_xy: tuple[float, float] = (0.51, 0.9)
    subtitle_xy: tuple[float, float] = (0.51, 0.85)
    title_fontsize: float = 14.0
    subtitle_fontsize: float = 10.0
