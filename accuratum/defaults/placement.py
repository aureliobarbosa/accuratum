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

The checks above compare anchor points only. On top of them each label's
text box is estimated in data units (``em`` is the font size there, see
:func:`font_size_in_data_units`):

- A label moves outward from its endpoint (down/up for hours, left/right
  for days) until its box clears every line. The solstice curves are
  slanted, so a box touching the endpoint cuts them with a corner.
- If that is blocked within ``MAX_PUSH_EM``, the label tries the direction
  its line would continue past the endpoint, aligned to that side. Lines
  that meet a steep solstice curve almost flat (high latitudes) have their
  neighbours just above and below, and free space straight ahead.
- A label with no clear spot either way sits among the lines (its line
  ends mid-drawing, the sun under the horizon cut) and is hidden.
- A label whose box overlaps an already placed one is hidden: anchors can
  be far apart while the texts overlap (``12/21`` extends left of its
  anchor, over an ``11h`` beside it).

Suppressed labels are not dropped: they come back with ``hidden=True`` so a
human can restore one by editing the project file. Each endpoint label has
its own selector (``end: "start" | "end"``), so it can be edited alone.
"""

import math

import numpy as np

from accuratum.core.hints import RenderHints
from accuratum.core.plot import Label, Polyline

# Text metrics of matplotlib's default font (DejaVu Sans), in em.
CHAR_WIDTH_EM = {"/": 0.34}
DEFAULT_CHAR_WIDTH_EM = 0.64  # digits and "h"
TEXT_HEIGHT_EM = 1.03  # the tallest across dpi: small text is hinted to whole pixels (0.86 at 72 dpi)
AXES_MARGIN = 0.05  # matplotlib's default autoscale margin on each side

GAP_EM = 0.2  # distance from the endpoint to the label's near edge
PAD_EM = 0.1  # free space required around a label's box
PUSH_STEP_EM = 0.1
MAX_PUSH_EM = 2.0

Box = tuple[float, float, float, float]  # x0, y0, x1, y1


def font_size_in_data_units(polylines: list[Polyline], hints: RenderHints | None = None) -> float:
    """One em of label text in data units, as the matplotlib renderer draws
    *polylines* with *hints* (the defaults if ``None``).

    The axes keep an equal aspect, so the scale is set by whichever side of
    ``axes_rect`` the drawing (plus matplotlib's margins) fills first."""
    hints = hints or RenderHints()
    finite = [(p.xs[ok], p.ys[ok]) for p in polylines if (ok := np.isfinite(p.xs) & np.isfinite(p.ys)).any()]
    if not finite:
        return 0.0
    xs = np.concatenate([x for x, _ in finite])
    ys = np.concatenate([y for _, y in finite])
    span_x = max(float(np.ptp(xs)), 1e-9) * (1 + 2 * AXES_MARGIN)
    span_y = max(float(np.ptp(ys)), 1e-9) * (1 + 2 * AXES_MARGIN)
    width_pt = hints.figsize[0] * hints.axes_rect[2] * 72
    height_pt = hints.figsize[1] * hints.axes_rect[3] * 72
    points_per_unit = min(width_pt / span_x, height_pt / span_y)
    return hints.label_fontsize / points_per_unit


def text_box(x: float, y: float, text: str, ha: str, va: str, em: float) -> Box:
    """The box matplotlib draws *text* in, anchored at ``(x, y)``."""
    width = sum(CHAR_WIDTH_EM.get(c, DEFAULT_CHAR_WIDTH_EM) for c in text) * em
    height = TEXT_HEIGHT_EM * em
    x0 = {"left": x, "right": x - width}.get(ha, x - width / 2)
    y0 = {"bottom": y, "top": y - height}.get(va, y - height / 2)
    return (x0, y0, x0 + width, y0 + height)


def _segments(polylines: list[Polyline]) -> np.ndarray:
    """Every line segment as rows ``(x0, y0, x1, y1)``, non-finite ones dropped."""
    parts = [np.column_stack([p.xs[:-1], p.ys[:-1], p.xs[1:], p.ys[1:]]) for p in polylines if p.xs.size > 1]
    if not parts:
        return np.empty((0, 4))
    segs = np.concatenate(parts)
    return segs[np.isfinite(segs).all(axis=1)]


def _hits_segments(box: Box, segs: np.ndarray) -> bool:
    """Whether any segment crosses or lies inside *box* (Liang–Barsky clipping)."""
    x0, y0, x1, y1 = box
    sx, sy, ex, ey = segs.T
    near = (np.maximum(sx, ex) >= x0) & (np.minimum(sx, ex) <= x1)
    near &= (np.maximum(sy, ey) >= y0) & (np.minimum(sy, ey) <= y1)
    if not near.any():
        return False
    sx, sy, dx, dy = sx[near], sy[near], ex[near] - sx[near], ey[near] - sy[near]
    t0 = np.zeros_like(sx)
    t1 = np.ones_like(sx)
    ok = np.ones_like(sx, dtype=bool)
    for p, q in ((-dx, sx - x0), (dx, x1 - sx), (-dy, sy - y0), (dy, y1 - sy)):
        parallel = p == 0
        ok &= ~(parallel & (q < 0))
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.where(parallel, 0.0, q / np.where(parallel, 1.0, p))
        t0 = np.where(~parallel & (p < 0), np.maximum(t0, r), t0)
        t1 = np.where(~parallel & (p > 0), np.minimum(t1, r), t1)
    return bool((ok & (t0 <= t1)).any())


def _beyond(poly: Polyline, end: str, reach: float) -> tuple[float, float] | None:
    """Unit vector along which *poly* would continue past its *end*, taken
    over at least *reach* of the line so a kink in the last samples doesn't
    swing it; ``None`` for a line too short to have a direction."""
    pts = np.column_stack([poly.xs, poly.ys])
    pts = pts[np.isfinite(pts).all(axis=1)]
    if end == "start":
        pts = pts[::-1]
    if len(pts) < 2:
        return None
    tip = pts[-1]
    dist = np.hypot(*(tip - pts[:-1]).T)
    far = np.nonzero(dist >= reach)[0]
    back = pts[far[-1]] if far.size else pts[0]
    d = tip - back
    norm = math.hypot(*d)
    return None if norm == 0 else (float(d[0] / norm), float(d[1] / norm))


def _aligned(ux: float, uy: float) -> tuple[str, str]:
    """``(ha, va)`` that puts a label on the side of its anchor that ``(ux, uy)`` points to."""
    if abs(ux) >= abs(uy):
        return ("left" if ux > 0 else "right"), "center"
    return "center", ("bottom" if uy > 0 else "top")


def _grow(box: Box, by: float) -> Box:
    return (box[0] - by, box[1] - by, box[2] + by, box[3] + by)


def _overlap(a: Box, b: Box) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


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
    em: float | None = None,
) -> list[Label]:
    """Resolve label texts to ``Label`` objects with absolute positions.

    *dayline_labels* and *hourline_labels* are aligned with *polylines*
    (entries are ``None`` for unlabeled rows). The function walks
    daylines first so hour labels yield to day labels on collision.
    Hidden labels don't count as placed, so they never block others.

    *em* is the label font size in data units; ``None`` estimates it for the
    default render hints, ``0`` turns the text-box checks off.
    """
    if tolerance is None:
        tolerance = 0.04 * data_extent
    if plumb_exclusion is None:
        plumb_exclusion = 0.12 * data_extent
    if em is None:
        em = font_size_in_data_units(polylines)
    segs = _segments(polylines)

    placed: list[tuple[float, float, str, str]] = []
    boxes: list[Box] = []
    out: list[Label] = []

    def _clear_spot(
        x: float, y: float, text: str, ha: str, va: str, beyond: tuple[float, float] | None
    ) -> tuple[float, float, str, str, Box | None]:
        """The first anchor out from ``(x, y)`` whose box clears every line:
        along the default side first, then along *beyond*. Returns the anchor,
        its alignment and box; the first candidate and ``None`` if none clears."""
        default = ({"left": 1.0, "right": -1.0}.get(ha, 0.0), {"bottom": 1.0, "top": -1.0}.get(va, 0.0))
        tries = [(default, ha, va)] + ([(beyond, *_aligned(*beyond))] if beyond else [])
        steps = round((MAX_PUSH_EM - GAP_EM) / PUSH_STEP_EM)
        for (ux, uy), tha, tva in tries:
            for k in range(steps + 1):
                d = (GAP_EM + k * PUSH_STEP_EM) * em
                box = text_box(x + ux * d, y + uy * d, text, tha, tva, em)
                if not _hits_segments(_grow(box, PAD_EM * em), segs):
                    return x + ux * d, y + uy * d, tha, tva, box
        (ux, uy) = default
        return x + ux * GAP_EM * em, y + uy * GAP_EM * em, ha, va, None

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
        beyond: tuple[float, float] | None,
    ) -> None:
        side = va if axis == "x" else ha
        hidden = (exclusion > 0.0 and math.hypot(x, y) < exclusion) or any(
            (abs(px - x) < tolerance if axis == "x" else abs(py - y) < tolerance)
            and ((pkind, pside) == (kind, side) or (kind == "hourline" and pkind == "dayline"))
            for px, py, pkind, pside in placed
        )
        lx, ly, lha, lva, box = (x, y, ha, va, None) if em <= 0.0 else _clear_spot(x, y, text, ha, va, beyond)
        if em > 0.0 and not hidden:
            hidden = box is None or any(_overlap(_grow(box, PAD_EM * em), b) for b in boxes)
        out.append(Label(text=text, x=lx, y=ly, ha=lha, va=lva, kind=kind, selector=selector, hidden=hidden))
        if not hidden:
            placed.append((x, y, kind, side))
            if box is not None:
                boxes.append(box)

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
            beyond=_beyond(poly, "start", em),
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
            beyond=_beyond(poly, "end", em),
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
            beyond=_beyond(poly, "start", em),
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
            beyond=_beyond(poly, "end", em),
        )

    return out
