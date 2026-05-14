"""Solar geometry — Sun position and sunrise/sunset queries.

This is the bottom of the core stack. It knows about astropy and astroplan,
but nothing about sundial types, grids, or rendering.
"""

import numpy as np
from astroplan import Observer
from astropy.coordinates import AltAz, EarthLocation, get_sun
from astropy.time import Time
from astropy.units import deg


def build_altaz_frame(lat: float, lon: float) -> AltAz:
    """Local AltAz frame at *(lat, lon)*. Pressure = 0 skips refraction."""
    location = EarthLocation(lat=lat * deg, lon=lon * deg)
    return AltAz(location=location, pressure=0)


def get_sun_altaz(times: np.ndarray, frame: AltAz) -> tuple[np.ndarray, np.ndarray]:
    """Solar (alt_deg, az_deg) for each ``datetime64`` in *times*."""
    sun = get_sun(Time(times)).transform_to(frame)
    return sun.alt.value, sun.az.value  # type: ignore[return-value]


def get_sunrises_and_sunsets(
    dates: np.ndarray,
    lat: float,
    lon: float,
    horizon_deg: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """``(sunrises, sunsets)`` as ``datetime64[s]`` arrays for each date in *dates*.

    *dates* is an array of ``datetime64`` (any time-of-day component is
    ignored). *horizon_deg* is the altitude in degrees that defines
    rise/set; ``0`` is the geometric horizon.
    """
    observer = Observer(location=EarthLocation(lat=lat * deg, lon=lon * deg))
    midnights = Time([f"{d}T00:00:00" for d in dates], format="isot", scale="utc")
    sunrises = observer.sun_rise_time(midnights, which="next", horizon=horizon_deg * deg)
    sunsets = observer.sun_set_time(sunrises, which="next", horizon=horizon_deg * deg)
    return (
        sunrises.datetime64.astype("datetime64[s]"),  # type: ignore[attr-defined]
        sunsets.datetime64.astype("datetime64[s]"),  # type: ignore[attr-defined]
    )
