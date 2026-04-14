from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np

_UTC = ZoneInfo("UTC")

DEFAULT_SOLSTICE_DAY = 21


def get_solstices(
    reference_datetime: datetime,
    solstice_day: int = DEFAULT_SOLSTICE_DAY,
) -> tuple[datetime, datetime, datetime]:
    """Return (previous-year December, current-year June, current-year December) solstices.

    The timezone of ``reference_datetime`` is preserved on all returned values.
    """
    tz = reference_datetime.tzinfo
    year = reference_datetime.year
    first = datetime(year - 1, 12, solstice_day, tzinfo=tz)
    middle = datetime(year, 6, solstice_day, tzinfo=tz)
    last = datetime(year, 12, solstice_day, tzinfo=tz)
    return first, middle, last


def frame_periods(
    solstices: tuple[datetime, datetime, datetime],
) -> list[list[datetime]]:
    """Split the three solstices into two consecutive [start, end] periods."""
    first, middle, last = solstices
    return [[first, middle], [middle, last]]


def _period_edges_as_utc_hours(
    frame_period: list[datetime],
    sunrise: int,
) -> tuple[np.datetime64, np.datetime64]:
    if not (isinstance(frame_period, (list, tuple)) and len(frame_period) == 2):
        raise TypeError("frame_period must be a 2-element sequence of datetimes")

    start, end = frame_period
    if not (isinstance(start, datetime) and isinstance(end, datetime)):
        raise TypeError("frame_period elements must be datetime instances")

    def _to_utc_hour(dt: datetime) -> np.datetime64:
        return np.datetime64(
            dt.replace(hour=sunrise + 1).astimezone(_UTC).replace(tzinfo=None),
            "h",
        )

    return _to_utc_hour(start), _to_utc_hour(end)


def build_dayline_grid(
    frame_period: list[datetime],
    sunrise: int = 6,
    sunset: int = 18,
    day_step: timedelta = timedelta(days=7),
    time_step: timedelta = timedelta(minutes=1),
) -> np.ndarray:
    """Build a 2-D datetime64 grid for daylines (rows = days, columns = minutes)."""
    first_date, last_date = _period_edges_as_utc_hours(frame_period, sunrise)

    day_offset = np.timedelta64(timedelta(days=2), "D")
    days = np.arange(
        first_date,
        last_date + day_offset,
        np.timedelta64(day_step, "D"),
    )

    time_range = np.timedelta64(timedelta(hours=(sunset - 1) - (sunrise + 1)), "m")
    time_step_np = np.timedelta64(time_step, "m")
    times = np.arange(0, time_range + time_step_np, time_step_np)

    grid_times, grid_days = np.meshgrid(times, days)
    return grid_days + grid_times


def build_hourline_grid(
    frame_period: list[datetime],
    sunrise: int = 6,
    sunset: int = 18,
    day_step: timedelta = timedelta(days=1),
    time_step: timedelta = timedelta(minutes=10),
) -> np.ndarray:
    """Build a 2-D datetime64 grid for hourlines (rows = times, columns = days)."""
    first_date, last_date = _period_edges_as_utc_hours(frame_period, sunrise)

    time_range = np.timedelta64(timedelta(hours=(sunset - 1) - (sunrise + 1)), "m")
    time_step_np = np.timedelta64(time_step, "m")
    time_offset = np.timedelta64(timedelta(minutes=1), "s")
    times = np.arange(0, time_range + time_offset, time_step_np)

    day_offset = np.timedelta64(timedelta(days=1), "D")
    days = np.arange(
        first_date,
        last_date + day_offset,
        np.timedelta64(day_step, "D"),
    )

    grid_days, grid_times = np.meshgrid(days, times)
    return grid_days + grid_times
