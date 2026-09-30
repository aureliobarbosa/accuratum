"""Matplotlib renderer — turns a :class:`Plot` into a ``matplotlib.Figure``.

The renderer reads ``Plot`` and ``RenderHints`` and does *only* drawing:
positions, label texts, alignments, and overlay rects have all been
resolved upstream. No geometry, no label heuristics here.
"""

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from accuratum.core.hints import RenderHints
from accuratum.core.plot import Plot


def render(plot: Plot, hints: RenderHints | None = None) -> tuple[Figure, Axes]:
    """Render *plot* to a matplotlib ``(Figure, Axes)``."""
    hints = hints or RenderHints()
    fig = plt.figure(figsize=hints.figsize)
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

    for text, (x, y), size in (
        (plot.title, hints.title_xy, hints.title_fontsize),
        (plot.subtitle, hints.subtitle_xy, hints.subtitle_fontsize),
    ):
        if text:
            fig.text(x, y, text, fontsize=size, color=hints.label_color, ha="center", va="center")

    xp, yp = plot.plumb_xy
    ax.scatter(xp, yp, s=10, facecolors="none", edgecolors="k", linewidths=0.5, zorder=5)

    return fig, ax
