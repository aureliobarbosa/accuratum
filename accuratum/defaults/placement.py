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

Per-label overrides (:class:`accuratum.core.spec.LabelOverride`) apply
after the heuristic: a matching ``selector`` can ``hide``, ``rename``
(``text``), or nudge ``(dx, dy)`` a label.
"""

import math

from accuratum.core.metadata import selector_matches
from accuratum.core.plot import Label, Polyline
from accuratum.core.spec import LabelOverride


def _selector_for(poly: Polyline) -> dict:
    """The metadata-identity selector for *poly*'s label."""
    md = poly.metadata
    if md.get("kind") == "dayline":
        return {"kind": "dayline", "date": md["date"]}
    if md.get("kind") == "hourline":
        return {"kind": "hourline", "hour": md["hour"]}
    return {"kind": md.get("kind", "")}


def _apply_overrides(
    base: Label,
    overrides: list[LabelOverride],
) -> Label | None:
    """Apply matching overrides to *base*. Return ``None`` if hidden."""
    text = base.text
    x = base.x
    y = base.y
    for ov in overrides:
        if not selector_matches(ov.selector, base.selector):
            continue
        if ov.hidden:
            return None
        if ov.text is not None:
            text = ov.text
        x += ov.dx
        y += ov.dy
    if text == base.text and x == base.x and y == base.y:
        return base
    return Label(text=text, x=x, y=y, ha=base.ha, va=base.va, kind=base.kind, selector=base.selector)


def place_labels(
    polylines: list[Polyline],
    dayline_labels: list[str | None],
    hourline_labels: list[str | None],
    data_extent: float,
    overrides: list[LabelOverride] | None = None,
    tolerance: float | None = None,
    plumb_exclusion: float | None = None,
) -> list[Label]:
    """Resolve label texts to ``Label`` objects with absolute positions.

    *dayline_labels* and *hourline_labels* are aligned with *polylines*
    (entries are ``None`` for unlabeled rows). The function walks
    daylines first so hour labels yield to day labels on collision.
    """
    if tolerance is None:
        tolerance = 0.04 * data_extent
    if plumb_exclusion is None:
        plumb_exclusion = 0.12 * data_extent
    overrides = overrides or []

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
        if exclusion > 0.0 and math.hypot(x, y) < exclusion:
            return
        for px, py in placed:
            if axis == "x" and abs(px - x) < tolerance:
                return
            if axis == "y" and abs(py - y) < tolerance:
                return
        base = Label(text=text, x=x, y=y, ha=ha, va=va, kind=kind, selector=selector)
        resolved = _apply_overrides(base, overrides)
        if resolved is None:
            return
        out.append(resolved)
        placed.append((resolved.x, resolved.y))

    # Daylines first (shared placed list → hourlines yield to daylines).
    for poly, text in zip(polylines, dayline_labels):
        if text is None or poly.metadata.get("kind") != "dayline" or len(poly.xs) == 0:
            continue
        selector = _selector_for(poly)
        _try_place(
            float(poly.xs[0]),
            float(poly.ys[0]),
            text,
            ha="right",
            va="center",
            kind="dayline",
            selector=selector,
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
            selector=selector,
            axis="y",
            exclusion=0.0,
        )

    # Hourlines second.
    for poly, text in zip(polylines, hourline_labels):
        if text is None or poly.metadata.get("kind") != "hourline" or len(poly.xs) == 0:
            continue
        selector = _selector_for(poly)
        _try_place(
            float(poly.xs[0]),
            float(poly.ys[0]),
            text,
            ha="center",
            va="top",
            kind="hourline",
            selector=selector,
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
            selector=selector,
            axis="x",
            exclusion=plumb_exclusion,
        )

    return out
