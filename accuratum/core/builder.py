"""``build_plot`` — orchestrates the Spec → Plot pipeline.

Pure top of the core stack: given a :class:`SundialSpec`, generate the
time grids, project them through the sundial type's projection, attach
metadata, select and place the default labels, and return a
:class:`Plot`.

No I/O, no matplotlib. The renderer consumes the returned ``Plot``.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np

from accuratum.core.astronomy import build_altaz_frame, get_sun_altaz
from accuratum.core.plot import Plot, Polyline, data_extent
from accuratum.core.spec import SundialSpec
from accuratum.core.timegrid import dayline_grid, hourline_grid
from accuratum.defaults.labels import select_dayline_labels, select_hourline_labels
from accuratum.defaults.placement import place_labels
from accuratum.projections.accuratum import project as project_accuratum


def build_plot(spec: SundialSpec) -> Plot:
    """Return a :class:`Plot` for *spec*. Pure function (no I/O)."""
    if spec.sundial_type != "accuratum":
        raise ValueError(f"unsupported sundial_type: {spec.sundial_type!r}")

    tz = ZoneInfo(spec.location.timezone)
    frame = build_altaz_frame(spec.location.lat, spec.location.lon)

    dl_grid = dayline_grid(spec.timeframe, spec.location, spec.grid)
    hl_grid = hourline_grid(spec.timeframe, spec.location, spec.grid)

    dayline_polys = [_row_to_dayline(row, frame, tz, spec.plumb_length) for row in dl_grid]
    hourline_polys = [_row_to_hourline(row, frame, tz, spec.plumb_length) for row in hl_grid]
    polylines = dayline_polys + hourline_polys

    extent = data_extent(polylines)

    dl_labels = select_dayline_labels(polylines)
    hl_labels = select_hourline_labels(polylines, spec.grid.time_step_minutes)

    labels = place_labels(
        polylines,
        dl_labels,
        hl_labels,
        data_extent=extent,
    )

    return Plot(polylines=polylines, labels=labels, plumb_xy=(0.0, 0.0), data_extent=extent)


# --- internals ---------------------------------------------------------------


def _row_to_dayline(row: np.ndarray, frame, tz: ZoneInfo, plumb_length: float) -> Polyline:
    valid = row[~np.isnat(row)]
    if valid.size == 0:
        return Polyline(kind="dayline", xs=np.empty(0), ys=np.empty(0), metadata={})

    alt, az = get_sun_altaz(valid, frame)
    xs, ys = project_accuratum(alt, az, plumb_length)

    local = _utc_dt64_to_local_datetime(valid[0], tz)
    return Polyline(
        kind="dayline",
        xs=xs,
        ys=ys,
        metadata={"kind": "dayline", "date": local.strftime("%Y-%m-%d")},
    )


def _row_to_hourline(row: np.ndarray, frame, tz: ZoneInfo, plumb_length: float) -> Polyline:
    valid = row[~np.isnat(row)]
    if valid.size == 0:
        return Polyline(kind="hourline", xs=np.empty(0), ys=np.empty(0), metadata={})

    alt, az = get_sun_altaz(valid, frame)
    xs, ys = project_accuratum(alt, az, plumb_length)

    local = _utc_dt64_to_standard_time(valid[valid.size // 2], tz)
    target_hour, minute_offset = _canonical_hour(local.hour, local.minute)
    return Polyline(
        kind="hourline",
        xs=xs,
        ys=ys,
        metadata={"kind": "hourline", "hour": target_hour, "minute_offset": minute_offset},
    )


def _utc_dt64_to_local_datetime(dt64: np.datetime64, tz: ZoneInfo) -> datetime:
    utc_dt = dt64.astype("datetime64[s]").astype(datetime).replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(tz)


def _utc_dt64_to_standard_time(dt64: np.datetime64, tz: ZoneInfo) -> datetime:
    """Local *standard* time (DST removed) of *dt64*.

    An hour line is one fixed UTC time of day across the frame, so it can
    carry only one clock reading; a DST switch mid-frame would otherwise
    label neighbouring lines with different clocks. Sundials read standard
    time.
    """
    local = _utc_dt64_to_local_datetime(dt64, tz)
    return local - (local.dst() or timedelta(0))


def _canonical_hour(hour: int, minute: int) -> tuple[int, int]:
    """Return ``(target_hour, signed_offset_min)`` snapping to the nearest hour."""
    if minute <= 30:
        return hour, minute
    return (hour + 1) % 24, minute - 60
