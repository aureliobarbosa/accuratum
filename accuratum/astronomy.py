from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
from astroplan import Observer
from astropy.coordinates import AltAz, EarthLocation, get_sun
from astropy.time import Time
from astropy.units import deg

_UTC = ZoneInfo("UTC")


def build_altaz_frame(lat: float, lon: float) -> AltAz:
    """Build an AltAz reference frame for an observer on Earth's surface.

    Pressure is set to zero so astropy skips atmospheric refraction.
    """
    location = EarthLocation(lat=lat * deg, lon=lon * deg)
    return AltAz(location=location, pressure=0)


def grid_to_shadow_xy(
    grid: np.ndarray,
    frame: AltAz,
    plumb_length: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert a datetime64 grid into (x, y) shadow positions of a vertical plumb."""
    sun = get_sun(Time(grid)).transform_to(frame)
    sun_alt: np.ndarray = sun.alt.value  # type: ignore
    sun_az: np.ndarray = sun.az.value  # type: ignore

    shadow_length = plumb_length / np.tan(np.deg2rad(sun_alt))
    x = -shadow_length * np.sin(np.deg2rad(sun_az))
    y = shadow_length * np.cos(np.deg2rad(sun_az))
    return x, y


def get_sunrises_and_sunsets(
    dates: np.ndarray,
    lat: float,
    lon: float,
    horizon: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (sunrises, sunsets) as datetime64[s] arrays for each date in *dates*.

    *dates* must be an array of datetime64 values (one per day, at any time-of-day).
    *horizon* is the altitude in degrees used to define sunrise/sunset (0 = geometric horizon).
    """
    observer = Observer(location=EarthLocation(lat=lat * deg, lon=lon * deg))
    midnights = Time([f"{d}T00:00:00" for d in dates], format="isot", scale="utc")
    sunrises = observer.sun_rise_time(midnights, which="next", horizon=horizon * deg)
    sunsets = observer.sun_set_time(sunrises, which="next", horizon=horizon * deg)
    # return sunrises.datetime64.astype("datetime64[s]"), sunsets.datetime64.astype("datetime64[s]")  # type: ignore
    return sunrises.datetime64, sunsets.datetime64  # type: ignore


def smart_dayline_grid(
    frame_period: list[datetime],
    lat: float,
    lon: float,
    day_step: timedelta = timedelta(days=7),
    line_points: int = 500,
    horizon: float = 10.0,
) -> np.ndarray:
    """Build a 2-D datetime64[s] grid (days × daytime_points) bounded by 'horizon' degrees from solar horizon."""
    start, end = frame_period
    first = np.datetime64(start.astimezone(_UTC).replace(tzinfo=None), "D")
    last = np.datetime64(end.astimezone(_UTC).replace(tzinfo=None), "D")
    days = np.arange(first, last + np.timedelta64(1, "D"), np.timedelta64(day_step, "D"))

    rises, sets = get_sunrises_and_sunsets(days, lat, lon, horizon=horizon)

    alphas = np.linspace(0, 1, line_points)
    rises_s = rises[:, None]
    spans_s = (sets - rises)[:, None]
    return rises_s + spans_s * alphas


def smart_hourline_grid(
    frame_period: list[datetime],
    lat: float,
    lon: float,
    day_step: timedelta | np.timedelta64 = timedelta(days=1),
    time_step: timedelta | np.timedelta64 = timedelta(minutes=20),
    horizon: float = 10.0,
):  # -> np.ndarray:
    """Build a 2-D datetime64 grid for hourlines (rows = times, columns = days)."""
    first_day, last_day = frame_period
    first_day = np.datetime64(first_day.astimezone(_UTC).replace(tzinfo=None), "D")
    last_day = np.datetime64(last_day.astimezone(_UTC).replace(tzinfo=None), "D")
    day_step = np.timedelta64(day_step, "D")
    day_offset = np.timedelta64(1, "D")
    days = np.arange(first_day, last_day + day_offset, day_step)

    rises, sets = get_sunrises_and_sunsets(days, lat, lon, horizon=horizon)

    sunrise_hours = rises - rises.astype("datetime64[D]")
    sunset_hours = sets - sets.astype("datetime64[D]")

    min_sunrise = sunrise_hours.min()
    max_sunset = sunset_hours.max()

    # remove the timedelta(inside numpy), use numpy itself to represent those steps
    time_range = np.timedelta64(max_sunset - min_sunrise, "s")
    time_step = np.timedelta64(time_step, "s")
    time_offset = np.timedelta64(60, "s")
    times = np.arange(0, time_range + time_offset, time_step)

    grid_days, grid_times = np.meshgrid(days, times)
    grid = grid_days + grid_times

    return grid  # TEST THIS!!!

    # mask = rises <= grid <= sets

    # return np.where(mask, grid, np.datetime64("NaT"))


def compute_blocks(
    daylines_grid: np.ndarray,
    hourlines_grid: np.ndarray,
    lat: float,
    lon: float,
    plumb_length: float = 1.0,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Compute (x, y) shadow blocks for both dayline and hourline grids."""
    frame = build_altaz_frame(lat, lon)
    blocks_x: list[np.ndarray] = []
    blocks_y: list[np.ndarray] = []
    for grid in (daylines_grid, hourlines_grid):
        x, y = grid_to_shadow_xy(grid, frame, plumb_length=plumb_length)
        blocks_x.append(x)
        blocks_y.append(y)
    return blocks_x, blocks_y
