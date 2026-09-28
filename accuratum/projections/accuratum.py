"""Accuratum projection — vertical plumb on horizontal ground.

Pure math: takes solar (alt, az) angles, returns 2-D shadow coordinates.
No astropy, no datetimes, no spec types. This is the interface that
future sundial types (vertical wall, equatorial, analemmatic) will
parallel.

Convention: +y points geographic north, -x points east
(az=90° east → x = -sin(90°) = -1).
"""

import numpy as np


def project(
    alt_deg: np.ndarray,
    az_deg: np.ndarray,
    plumb_length: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Project solar angles to plumb-shadow ``(x, y)`` coordinates.

    Returns NaN/inf where the sun is at or below the horizon (``alt ≤ 0``);
    callers are expected to filter those, or feed only above-horizon samples.
    """
    alt_rad = np.deg2rad(alt_deg)
    az_rad = np.deg2rad(az_deg)
    shadow_length = plumb_length / np.tan(alt_rad)
    return -shadow_length * np.sin(az_rad), shadow_length * np.cos(az_rad)
