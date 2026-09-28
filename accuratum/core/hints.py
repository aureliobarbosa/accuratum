"""Render-side knobs — separate from :class:`SundialSpec` to keep specs portable.

``RenderHints`` carries how a plot is drawn: overlay images, canvas size in
millimeters, fonts, colors. A project saves them next to the spec (in
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
    overlays: list[Overlay] = field(default_factory=list)
    figsize: tuple[float, float] = (8.0, 6.0)
    canvas_size_mm: tuple[float, float] | None = None
    units: str = "mm"
    line_color: str = "green"
    line_width: float = 0.5
    label_color: str = "black"
    label_fontsize: float = 7.0
