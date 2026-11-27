"""Default endpoint placement and collision suppression.

Heuristic ported from the ``labels`` branch (see ``docs/LESSONS_LABELS.md``):

- Daylines: ``MM/DD`` label to the LEFT of the first sample, to the RIGHT
  of the last. 1-D collision check on ``|Δy|``.
- Hourlines: ``HHh`` label BELOW the lower endpoint, ABOVE the upper one.
  The side comes from geometry, not from sample order: a line runs up in
  the Dec→Jun frame and down in the Jun→Dec frame (issue #4: "below the
  first sample" put both labels on the drawing there). 1-D collision check
  on ``|Δx|``. Endpoints inside the plumb-exclusion disk
  are dropped (the noon cluster is hopeless).
- Labels collide only with labels on the same side (same kind and
  alignment, i.e. left/right or below/above): a
  line's two endpoints nearly share y (daylines) or x (hourlines), so a
  check against every label hid each right/top label behind its own twin.
- Hour labels also yield to every day label on ``|Δx|`` (days are placed
  first), since both converge at the period edges.
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

    placed: list[tuple[float, float, str, str]] = []
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
        side = va if axis == "x" else ha
        hidden = (exclusion > 0.0 and math.hypot(x, y) < exclusion) or any(
            (abs(px - x) < tolerance if axis == "x" else abs(py - y) < tolerance)
            and ((pkind, pside) == (kind, side) or (kind == "hourline" and pkind == "dayline"))
            for px, py, pkind, pside in placed
        )
        out.append(Label(text=text, x=x, y=y, ha=ha, va=va, kind=kind, selector=selector, hidden=hidden))
        if not hidden:
            placed.append((x, y, kind, side))

    # Daylines first, so hourlines yield to daylines.
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

    # Hourlines second. The lower endpoint's label hangs below it, the upper
    # one's sits above it, whichever end the samples start from.
    for poly, text in zip(polylines, hourline_labels):
        if text is None or poly.metadata.get("kind") != "hourline" or len(poly.xs) == 0:
            continue
        runs_up = poly.ys[0] <= poly.ys[-1]
        _try_place(
            float(poly.xs[0]),
            float(poly.ys[0]),
            text,
            ha="center",
            va="top" if runs_up else "bottom",
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
            va="bottom" if runs_up else "top",
            kind="hourline",
            selector=_selector_for(poly, "end"),
            axis="x",
            exclusion=plumb_exclusion,
        )

    return out
