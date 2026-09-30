"""Matplotlib renderer — turns a :class:`Plot` into a ``matplotlib.Figure``.

The renderer reads ``Plot`` and ``RenderHints`` and does *only* drawing:
positions, label texts, alignments, and overlay rects have all been
resolved upstream. No geometry, no label heuristics here.
"""

import matplotlib.image as mpimg
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.text import Text

from accuratum.core.hints import RenderHints
from accuratum.core.plot import Plot


def render(plot: Plot, hints: RenderHints | None = None) -> tuple[Figure, Axes]:
    """Render *plot* to a matplotlib ``(Figure, Axes)``."""
    hints = hints or RenderHints()
    fig = Figure(figsize=hints.figsize)  # not pyplot: no global state, safe across threads
    ax = fig.add_axes(hints.axes_rect)
    ax.set_aspect("equal")
    ax.set_anchor("N")  # hug the header band, whatever the drawing's shape
    for spine in ax.spines.values():
        spine.set_visible(False)

    colors = {"dayline": hints.dayline_color, "hourline": hints.hourline_color}
    for poly in plot.polylines:
        if poly.xs.size == 0:
            continue
        ax.plot(poly.xs, poly.ys, "-", color=colors[poly.kind], linewidth=hints.line_width)

    for label in plot.labels:
        if label.hidden:
            continue
        ax.text(
            label.x,
            label.y,
            label.text,
            color=hints.label_color,
            fontsize=hints.label_fontsize,
            ha=label.ha,
            va=label.va,
        )

    for overlay in hints.overlays:
        img = mpimg.imread(overlay.image_path)
        overlay_ax = fig.add_axes(overlay.rect, zorder=10)
        overlay_ax.imshow(img)
        overlay_ax.axis("off")

    header = [
        fig.text(x, y, text, fontsize=size, color=hints.label_color, ha="center", va="center")
        for text, (x, y), size in (
            (plot.title, hints.title_xy, hints.title_fontsize),
            (plot.subtitle, hints.subtitle_xy, hints.subtitle_fontsize),
        )
        if text
    ]
    _fit_between_overlays(fig, header, hints)

    xp, yp = plot.plumb_xy
    ax.scatter(xp, yp, s=10, facecolors="none", edgecolors="k", linewidths=0.5, zorder=5)

    return fig, ax


HEADER_PAD = 0.01  # figure fraction kept free on each side of the header texts


def _fit_between_overlays(fig: Figure, texts: list[Text], hints: RenderHints) -> None:
    """Shrink the title and subtitle by one common factor until both fit
    between the overlays at their height (the logo and compass by default).

    One factor keeps the two in proportion. Text width grows linearly with
    font size, so a single measurement is enough."""
    if not texts:
        return
    renderer = FigureCanvasAgg(fig).get_renderer()
    to_figure = fig.transFigure.inverted()
    factor = 1.0
    for text in texts:
        box = text.get_window_extent(renderer).transformed(to_figure)
        center = text.get_position()[0]
        left, right = 0.0, 1.0
        for overlay in hints.overlays:
            x0, y0, width, height = overlay.rect
            if y0 > box.y1 or y0 + height < box.y0:
                continue  # not at this text's height
            if x0 + width <= center:
                left = max(left, x0 + width)
            elif x0 >= center:
                right = min(right, x0)
        room = 2 * (min(center - left, right - center) - HEADER_PAD)
        if box.width > room > 0:
            factor = min(factor, room / box.width)
    if factor < 1.0:
        for text in texts:
            text.set_fontsize(text.get_fontsize() * factor)
