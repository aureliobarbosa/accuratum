import numpy as np
from astropy.coordinates import AltAz, EarthLocation, get_sun
from astropy.time import Time
from astropy.units import deg


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
