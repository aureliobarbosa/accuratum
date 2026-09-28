"""Default endpoint placement and collision suppression.

Heuristic ported from the ``labels`` branch (see ``docs/LESSONS_LABELS.md``):

- Daylines: ``MM/DD`` label to the LEFT of the first sample, to the RIGHT
  of the last. 1-D collision check on ``|Δy|``.
- Hourlines: ``HHh`` label BELOW the first sample, ABOVE the last. 1-D
  collision check on ``|Δx|``. Endpoints inside the plumb-exclusion disk
  are dropped (the noon cluster is hopeless).
- The same ``placed`` list is threaded through both passes so hour labels
  yield to day labels on collision.
- Tolerance and exclusion default to ``0.04 × data_extent`` and
  ``0.12 × data_extent`` respectively.

Suppressed labels are not dropped: they come back with ``hidden=True`` so a
human can restore one by editing the project file. Each endpoint label has
its own selector (``end: "start" | "end"``), so it can be edited alone.
"""

import math

from accuratum.core.plot import Label, Polyline


def _selector_for(poly: Polyline, end: str) -> dict:
    """The identity selector for the label at *end* (``"start"``/``"end"``) of *poly*."""
    md = poly.metadata
    if md.get("kind") == "dayline":
        return {"kind": "dayline", "date": md["date"], "end": end}
    if md.get("kind") == "hourline":
        return {"kind": "hourline", "hour": md["hour"], "end": end}
    return {"kind": md.get("kind", ""), "end": end}


def place_labels(
    polylines: list[Polyline],
    dayline_labels: list[str | None],
    hourline_labels: list[str | None],
    data_extent: float,
    tolerance: float | None = None,
    plumb_exclusion: float | None = None,
) -> list[Label]:
    """Resolve label texts to ``Label`` objects with absolute positions.

    *dayline_labels* and *hourline_labels* are aligned with *polylines*
    (entries are ``None`` for unlabeled rows). The function walks
    daylines first so hour labels yield to day labels on collision.
    Hidden labels don't count as placed, so they never block others.
    """
    if tolerance is None:
        tolerance = 0.04 * data_extent
    if plumb_exclusion is None:
        plumb_exclusion = 0.12 * data_extent

    placed: list[tuple[float, float]] = []
    out: list[Label] = []

    def _try_place(
        x: float,
        y: float,
        text: str,
        ha: str,
        va: str,
        kind: str,
        selector: dict,
        axis: str,
        exclusion: float,
    ) -> None:
        hidden = (exclusion > 0.0 and math.hypot(x, y) < exclusion) or any(
            abs(px - x) < tolerance if axis == "x" else abs(py - y) < tolerance for px, py in placed
        )
        out.append(Label(text=text, x=x, y=y, ha=ha, va=va, kind=kind, selector=selector, hidden=hidden))
        if not hidden:
            placed.append((x, y))

    # Daylines first (shared placed list → hourlines yield to daylines).
    for poly, text in zip(polylines, dayline_labels):
        if text is None or poly.metadata.get("kind") != "dayline" or len(poly.xs) == 0:
            continue
        _try_place(
            float(poly.xs[0]),
            float(poly.ys[0]),
            text,
            ha="right",
            va="center",
            kind="dayline",
            selector=_selector_for(poly, "start"),
            axis="y",
            exclusion=0.0,
        )
        _try_place(
            float(poly.xs[-1]),
            float(poly.ys[-1]),
            text,
            ha="left",
            va="center",
            kind="dayline",
            selector=_selector_for(poly, "end"),
            axis="y",
            exclusion=0.0,
        )

    # Hourlines second.
    for poly, text in zip(polylines, hourline_labels):
        if text is None or poly.metadata.get("kind") != "hourline" or len(poly.xs) == 0:
            continue
        _try_place(
            float(poly.xs[0]),
            float(poly.ys[0]),
            text,
            ha="center",
            va="top",
            kind="hourline",
            selector=_selector_for(poly, "start"),
            axis="x",
            exclusion=plumb_exclusion,
        )
        _try_place(
            float(poly.xs[-1]),
            float(poly.ys[-1]),
            text,
            ha="center",
            va="bottom",
            kind="hourline",
            selector=_selector_for(poly, "end"),
            axis="x",
            exclusion=plumb_exclusion,
        )

    return out
