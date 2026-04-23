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
    sun_alt = sun.alt.value
    sun_az = sun.az.value

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
    return sunrises.datetime64.astype("datetime64[s]"), sunsets.datetime64.astype("datetime64[s]")


def smart_dayline_grid(
    frame_period: list[datetime],
    lat: float,
    lon: float,
    day_step: timedelta = timedelta(days=7),
    line_points: int = 500,
) -> np.ndarray:
    """Build a 2-D datetime64[s] grid (days × daytime_points) bounded by the 10° solar horizon."""
    start, end = frame_period
    first = np.datetime64(start.astimezone(_UTC).replace(tzinfo=None), "D")
    last = np.datetime64(end.astimezone(_UTC).replace(tzinfo=None), "D")
    days = np.arange(first, last + np.timedelta64(1, "D"), np.timedelta64(day_step, "D"))

    rises, sets = get_sunrises_and_sunsets(days, lat, lon, horizon=10.0)

    alphas = np.linspace(0, 1, line_points)  # (line_points,)
    rises_s = rises.astype(np.int64)[:, None]  # (n_days, 1)
    spans_s = (sets.astype(np.int64) - rises.astype(np.int64))[:, None]  # (n_days, 1)
    return (rises_s + spans_s * alphas).astype(np.int64).view("datetime64[s]")


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
