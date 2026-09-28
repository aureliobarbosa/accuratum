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
