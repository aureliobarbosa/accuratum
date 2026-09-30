"""Solar geometry — Sun position and sunrise/sunset queries.

This is the bottom of the core stack. It knows about astropy and astroplan,
but nothing about sundial types, grids, or rendering.
"""

import warnings

import numpy as np
from astroplan import Observer, TargetNeverUpWarning
from astropy.coordinates import AltAz, EarthLocation, get_sun
from astropy.time import Time
from astropy.units import deg
from astropy.utils import iers

# Use the IERS and leap-second tables bundled with astropy (astropy-iers-data,
# pinned by uv.lock) instead of downloading fresh ones at run time. A server
# instance then needs no network, no writable home and no IERS server. The
# cost is up to ~0.9 s of UT1-UTC error, invisible on a sundial.
iers.conf.auto_download = False
iers.conf.auto_max_age = None


def build_altaz_frame(lat: float, lon: float) -> AltAz:
    """Local AltAz frame at *(lat, lon)*. Pressure = 0 skips refraction."""
    location = EarthLocation(lat=lat * deg, lon=lon * deg)
    return AltAz(location=location, pressure=0)


def get_sun_altaz(times: np.ndarray, frame: AltAz) -> tuple[np.ndarray, np.ndarray]:
    """Solar (alt_deg, az_deg) for each ``datetime64`` in *times*."""
    sun = get_sun(Time(times)).transform_to(frame)
    return sun.alt.value, sun.az.value  # type: ignore[return-value]


def local_mean_midnights(dates: np.ndarray, lon: float) -> np.ndarray:
    """Local mean midnight of each date, as UTC ``datetime64[s]``.

    That is 00 UTC shifted by the longitude (4 min per degree, rounded to
    the minute). Anchoring days at 00 UTC instead splits the local day in
    two wherever it straddles 00 UTC (the Americas' west, Asia, Oceania).
    """
    return dates.astype("datetime64[D]").astype("datetime64[s]") - np.timedelta64(round(lon * 4), "m")


def get_sunrises_and_sunsets(
    dates: np.ndarray,
    lat: float,
    lon: float,
    horizon_deg: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """``(sunrises, sunsets)`` as ``datetime64[s]`` arrays for each date in *dates*.

    *dates* is an array of ``datetime64`` (any time-of-day component is
    ignored). The search starts at each date's local mean midnight (see
    :func:`local_mean_midnights`), so rise and set belong to the same local
    day at any longitude. *horizon_deg* is the altitude in degrees that defines
    rise/set; ``0`` is the geometric horizon. Days when the sun never
    climbs above it (high-latitude winters) are ``NaT`` in both arrays.
    """
    observer = Observer(location=EarthLocation(lat=lat * deg, lon=lon * deg))
    midnights = Time(local_mean_midnights(dates, lon), scale="utc")
    with warnings.catch_warnings():
        # Expected past |lat| ≈ 56.5° with a 10° cut; those days become NaT.
        warnings.simplefilter("ignore", TargetNeverUpWarning)
        sunrises = observer.sun_rise_time(midnights, which="next", horizon=horizon_deg * deg)
        never_up = np.broadcast_to(np.ma.getmaskarray(sunrises.jd), midnights.shape)
        # A masked Time can't feed sun_set_time, so search from midnight on those days.
        sunrises = Time(np.where(never_up, midnights.jd, sunrises.unmasked.jd), format="jd", scale="utc")
        sunsets = observer.sun_set_time(sunrises, which="next", horizon=horizon_deg * deg)
    never_up = never_up | np.ma.getmaskarray(sunsets.jd)
    nat = np.datetime64("NaT", "s")
    return (
        np.where(never_up, nat, sunrises.datetime64.astype("datetime64[s]")),  # type: ignore[attr-defined]
        np.where(never_up, nat, sunsets.unmasked.datetime64.astype("datetime64[s]")),  # type: ignore[attr-defined]
    )
