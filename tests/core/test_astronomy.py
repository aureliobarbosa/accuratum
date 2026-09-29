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
