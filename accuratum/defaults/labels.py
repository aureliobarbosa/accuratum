"""Default label-text selection rules.

These are pure functions over a list of :class:`Polyline` and produce a
parallel list of label strings (or ``None`` for rows that should not be
labeled). Placement (positions + collision suppression) is a separate
pass in :mod:`accuratum.defaults.placement`.

Rules (ported from the ``labels`` branch — see ``docs/LESSONS_LABELS.md``):

- Daylines: one ``MM/DD`` label per local-month transition. The first
  dayline whose local month differs from the last labeled one gets the
  label; rows in the same month return ``None``.
- Hourlines: one ``HHh`` label per row whose canonical hour falls within
  ``time_step/2`` of the actual sampled time.

Both functions are deterministic and free of I/O.
"""

from accuratum.core.plot import Polyline


def select_dayline_labels(polylines: list[Polyline]) -> list[str | None]:
    """Return labels parallel to *polylines*. Non-dayline rows yield ``None``."""
    labels: list[str | None] = []
    last_month: int | None = None
    for poly in polylines:
        if poly.metadata.get("kind") != "dayline":
            labels.append(None)
            continue
        date = poly.metadata["date"]  # "YYYY-MM-DD" in local tz
        month = int(date[5:7])
        day = int(date[8:10])
        if month != last_month:
            labels.append(f"{month:02d}/{day:02d}")
            last_month = month
        else:
            labels.append(None)
    return labels


def select_hourline_labels(
    polylines: list[Polyline],
    time_step_minutes: int,
) -> list[str | None]:
    """Return labels parallel to *polylines*. Non-hourline rows yield ``None``.

    A row is labeled iff its ``minute_offset`` lies within ``±time_step/2``
    of the canonical hour; the label is the metadata's ``hour`` value,
    formatted ``HHh``.
    """
    tol = time_step_minutes / 2
    labels: list[str | None] = []
    for poly in polylines:
        if poly.metadata.get("kind") != "hourline":
            labels.append(None)
            continue
        offset = poly.metadata["minute_offset"]
        if abs(offset) <= tol:
            hour = poly.metadata["hour"]
            labels.append(f"{hour:02d}h")
        else:
            labels.append(None)
    return labels
