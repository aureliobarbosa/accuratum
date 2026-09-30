import numpy as np
import pytest
from astropy.coordinates import AltAz

from accuratum.core.astronomy import build_altaz_frame, get_sun_altaz, get_sunrises_and_sunsets

LAT = -15.6006489  # FUP Planaltina
LON = -47.6580608


def test_build_altaz_frame_pressure_is_zero():
    frame = build_altaz_frame(LAT, LON)
    assert isinstance(frame, AltAz)
    assert frame.pressure.value == 0


def test_get_sun_altaz_at_local_noon_is_above_horizon():
    # 2026-03-21 (equinox) at solar noon UTC -> sun should be high in the sky
    times = np.array(["2026-03-21T15:00:00"], dtype="datetime64[s]")
    frame = build_altaz_frame(LAT, LON)
    alt, az = get_sun_altaz(times, frame)
    assert alt.shape == (1,)
    assert az.shape == (1,)
    assert alt[0] > 30.0  # comfortably above horizon at -15° lat


@pytest.fixture(scope="module")
def sun_times():
    dates = np.array(["2026-06-21", "2026-09-21", "2026-12-21"], dtype="datetime64[D]")
    return get_sunrises_and_sunsets(dates, lat=LAT, lon=LON)


def test_get_sunrises_and_sunsets_shape_and_dtype(sun_times):
    rises, sets = sun_times
    assert rises.shape == (3,)
    assert sets.shape == (3,)
    assert rises.dtype == np.dtype("datetime64[s]")
    assert sets.dtype == np.dtype("datetime64[s]")


def test_sunsets_after_sunrises(sun_times):
    rises, sets = sun_times
    assert np.all(sets.astype(np.int64) > rises.astype(np.int64))


def test_horizon_shifts_rise_and_set():
    dates = np.array(["2026-06-21", "2026-09-21", "2026-12-21"], dtype="datetime64[D]")
    rises_0, sets_0 = get_sunrises_and_sunsets(dates, lat=LAT, lon=LON, horizon_deg=0.0)
    rises_10, sets_10 = get_sunrises_and_sunsets(dates, lat=LAT, lon=LON, horizon_deg=10.0)
    assert np.all(rises_10.astype(np.int64) > rises_0.astype(np.int64))
    assert np.all(sets_10.astype(np.int64) < sets_0.astype(np.int64))


def test_days_without_the_sun_above_the_horizon_are_nat():
    # At 62° N the winter-solstice noon altitude is ~4.6°, below a 10° cut.
    dates = np.array(["2026-11-01", "2026-12-21"], dtype="datetime64[D]")
    rises, sets = get_sunrises_and_sunsets(dates, lat=62.0, lon=-47.92, horizon_deg=10.0)
    assert rises.dtype == np.dtype("datetime64[s]")
    assert list(np.isnat(rises)) == [False, True]
    assert list(np.isnat(sets)) == [False, True]
    assert sets[0] > rises[0]


@pytest.mark.parametrize("lon", [-170.0, 170.0])
def test_rise_and_set_fall_on_the_local_day(lon):
    """The search starts at local mean midnight, so rise and set are the
    same local day's, whatever the longitude."""
    dates = np.array(["2026-03-21"], dtype="datetime64[D]")
    rises, sets = get_sunrises_and_sunsets(dates, lat=0.0, lon=lon)
    local_midnight = dates.astype("datetime64[s]") - np.timedelta64(round(lon * 4), "m")
    hours_after = (rises - local_midnight).astype("timedelta64[m]").astype(int) / 60
    assert 5 < hours_after[0] < 7
    assert 11 < (sets - rises).astype("timedelta64[m]").astype(int)[0] / 60 < 13


def test_sun_positions_need_no_download(tmp_path):
    # A new server instance has an empty cache and must not fetch IERS or
    # leap-second tables at run time: it uses the ones bundled with astropy.
    import os
    import subprocess
    import sys

    script = """
import socket, warnings

def offline(*args, **kwargs):
    raise OSError("network access attempted")

socket.socket.connect = offline
socket.create_connection = offline
warnings.simplefilter("error")  # a failed download only warns

import numpy as np
from accuratum.core.astronomy import build_altaz_frame, get_sun_altaz, get_sunrises_and_sunsets

times = np.array(["2026-03-21T15:00:00"], dtype="datetime64[s]")
get_sun_altaz(times, build_altaz_frame(-15.6, -47.66))
get_sunrises_and_sunsets(np.array(["2026-03-21"], dtype="datetime64[D]"), -15.6, -47.66)
"""
    env = {k: v for k, v in os.environ.items() if not k.startswith("XDG_")}
    env["HOME"] = str(tmp_path)  # astropy's cache lives in ~/.astropy
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[-2000:]
