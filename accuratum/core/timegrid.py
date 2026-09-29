"""Time-grid builders — Spec-driven datetime64 arrays for daylines and hourlines.

These functions take :class:`SundialSpec` components (``TimeFrame``,
``Location``, ``GridConfig``) and return the 2-D ``datetime64`` grids that
the projection layer turns into shadow polylines.

Knowing about astronomy (rise/set times) is fine; knowing about projection
or rendering is not.
"""

import numpy as np

from accuratum.core.astronomy import get_sunrises_and_sunsets, local_mean_midnights
from accuratum.core.spec import GridConfig, Location, TimeFrame


def _frame_days(timeframe: TimeFrame) -> tuple[np.datetime64, np.datetime64]:
    """First and last *local* dates of the frame, as ``datetime64[D]``.

    Each date stands for a local day starting at local mean midnight (see
    :func:`~accuratum.core.astronomy.local_mean_midnights`). UTC dates would
    start a frame a day early east of Greenwich (21 Jun 00:00 in Sydney is
    20 Jun in UTC).
    """
    return np.datetime64(timeframe.start.date(), "D"), np.datetime64(timeframe.end.date(), "D")


def dayline_grid(timeframe: TimeFrame, location: Location, grid: GridConfig) -> np.ndarray:
    """2-D ``datetime64[s]`` grid (rows = days, cols = within-day samples).

    Each row spans that day's sun-up window bounded by
    ``grid.horizon_degrees``, sampled at ``grid.line_points`` evenly-spaced
    instants.
    """
    first, last = _frame_days(timeframe)
    step = np.timedelta64(grid.dayline_day_step_days, "D")
    days = np.arange(first, last + np.timedelta64(1, "D"), step)

    rises, sets = get_sunrises_and_sunsets(days, location.lat, location.lon, horizon_deg=grid.horizon_degrees)
    alphas = np.linspace(0, 1, grid.line_points)
    rises_s = rises[:, None]
    spans_s = (sets - rises)[:, None]
    return rises_s + spans_s * alphas


def hourline_grid(timeframe: TimeFrame, location: Location, grid: GridConfig) -> np.ndarray:
    """2-D ``datetime64[s]`` grid (rows = times-of-day, cols = days).

    Out-of-window samples (before sunrise / after sunset on a given day,
    relative to ``grid.horizon_degrees``) are masked as ``NaT`` so callers
    can drop them per row. So are whole days when the sun stays below it.
    """
    first, last = _frame_days(timeframe)
    day_step = np.timedelta64(grid.hourline_day_step_days, "D")
    days = np.arange(first, last + np.timedelta64(1, "D"), day_step)

    rises, sets = get_sunrises_and_sunsets(days, location.lat, location.lon, horizon_deg=grid.horizon_degrees)
    rises = rises.reshape(1, -1)
    sets = sets.reshape(1, -1)
    midnights = local_mean_midnights(days, location.lon).reshape(1, -1)

    minute = np.timedelta64(1, "m")
    sunrise_hours = (rises - midnights).astype("timedelta64[m]") + minute
    sunset_hours = (sets - midnights).astype("timedelta64[m]") - minute

    # Days without sun above the cut are NaT; they'd poison min/max.
    lit = ~np.isnat(rises)
    min_sunrise = sunrise_hours[lit].min()
    max_sunset = sunset_hours[lit].max()
    days_anchored = midnights.ravel() + min_sunrise

    time_range = np.timedelta64(max_sunset - min_sunrise, "m")
    time_step = np.timedelta64(grid.time_step_minutes, "m")
    times = np.arange(0, time_range + minute, time_step)

    grid_times, grid_days = np.meshgrid(times, days_anchored, indexing="ij")
    raw = grid_days + grid_times

    mask = (rises <= raw) & (raw <= sets)
    return np.where(mask, raw, np.datetime64("NaT")).astype("datetime64[s]")
