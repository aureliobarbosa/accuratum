from typing import Optional, Sequence

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure


def plot_solar_clock(
    blocks_x: Sequence,
    blocks_y: Sequence,
    logos: Optional[Sequence[tuple[str, tuple[float, float, float, float]]]] = None,
    plumb_xy: tuple[float, float] = (0.0, 0.0),
    line_color: str = "green",
    line_width: float = 0.5,
    figsize: tuple[float, float] = (8.0, 6.0),
) -> tuple[Figure, Axes]:
    """Plot shadow-line blocks on a square-aspect matplotlib figure.

    Parameters
    ----------
    blocks_x, blocks_y:
        Lists/tuples of 2-D arrays; each row within an array becomes one line.
    logos:
        Optional list of (image_path, (left, bottom, width, height)) pairs used
        to place logos on the figure in figure coordinates.
    plumb_xy:
        Position of the plumb marker, in the same coordinate system as the
        shadow blocks.
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_aspect("equal")

    for x, y in zip(blocks_x, blocks_y):
        for row in range(len(x)):
            ax.plot(x[row], y[row], "-", color=line_color, linewidth=line_width)

    if logos:
        for image_path, rect in logos:
            logo = mpimg.imread(image_path)
            logo_ax = fig.add_axes(rect, zorder=10)
            logo_ax.imshow(logo)
            logo_ax.axis("off")

    xp, yp = plumb_xy
    ax.scatter(
        xp,
        yp,
        s=10,
        facecolors="none",
        edgecolors="k",
        linewidths=0.5,
        zorder=5,
    )

    return fig, ax
