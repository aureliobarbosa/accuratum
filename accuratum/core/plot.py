"""In-memory plot representation — the output of ``build_plot``.

A ``Plot`` is the contract between the core pipeline and the renderers.
It carries everything a renderer needs (polylines, labels, plumb
position, data extent) and nothing it doesn't (no matplotlib, no astropy).
Overlay images and other rendering concerns live in
:mod:`accuratum.core.hints`.

Unlike ``SundialSpec``, a ``Plot`` is not required to be JSON-serializable
— it holds numpy arrays for the polyline samples.
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Polyline:
    """One polyline (dayline or hourline) as a pair of 1-D arrays.

    ``metadata`` follows the contract in :mod:`accuratum.core.metadata`:
    daylines carry ``{"kind": "dayline", "date": "YYYY-MM-DD"}``,
    hourlines carry ``{"kind": "hourline", "hour": int, "minute": int}``.
    Overrides match polylines by querying this dict.
    """

    kind: str
    xs: np.ndarray
    ys: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Label:
    """A text label resolved to absolute data coordinates.

    ``selector`` identifies the label: the polyline identity plus the
    endpoint, e.g. ``{"kind": "hourline", "hour": 7, "end": "start"}``.
    SVG output emits it as an ``id=`` attribute (enabling Inkscape nudges).
    ``hidden`` labels were suppressed by the placement heuristic (or by
    hand); they stay in the data so they can be restored, but renderers
    skip them.
    """

    text: str
    x: float
    y: float
    ha: str
    va: str
    kind: str
    selector: dict[str, Any] = field(default_factory=dict)
    hidden: bool = False


@dataclass(frozen=True)
class Plot:
    polylines: list[Polyline]
    labels: list[Label]
    plumb_xy: tuple[float, float] = (0.0, 0.0)
    data_extent: float = 1.0


def data_extent(polylines: list[Polyline]) -> float:
    """Largest side of the bounding box of all finite polyline samples (1.0 if none)."""
    xs_min: list[float] = []
    xs_max: list[float] = []
    ys_min: list[float] = []
    ys_max: list[float] = []
    for poly in polylines:
        if poly.xs.size == 0:
            continue
        finite = np.isfinite(poly.xs) & np.isfinite(poly.ys)
        if not finite.any():
            continue
        xs_min.append(float(poly.xs[finite].min()))
        xs_max.append(float(poly.xs[finite].max()))
        ys_min.append(float(poly.ys[finite].min()))
        ys_max.append(float(poly.ys[finite].max()))
    if not xs_min:
        return 1.0
    return max(max(xs_max) - min(xs_min), max(ys_max) - min(ys_min))
