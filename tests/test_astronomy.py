from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from astropy.coordinates import AltAz

from accuratum.astronomy import (
    build_altaz_frame,
    compute_blocks,
    grid_to_shadow_xy,
)
from accuratum.datetime_utils import (
    build_dayline_grid,
    build_hourline_grid,
    frame_periods,
    get_solstices,
)


TZ_SP = ZoneInfo("America/Sao_Paulo")
# Brasília (FUP Planaltina area)
LAT = -15.6006489
LON = -47.6580608


@pytest.fixture(scope="module")
def grids():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    solstices = get_solstices(reference)
    period = frame_periods(solstices)[0]
    dl = build_dayline_grid(period, 6, 18, timedelta(days=7), timedelta(minutes=1))
    hl = build_hourline_grid(period, 6, 18, timedelta(days=1), timedelta(minutes=10))
    return dl, hl


def test_build_altaz_frame_returns_altaz():
    frame = build_altaz_frame(LAT, LON)
    assert isinstance(frame, AltAz)
    # Pressure should be zero to skip atmospheric refraction
    assert frame.pressure.value == 0


def test_grid_to_shadow_xy_shape_matches_input(grids):
    dl, _ = grids
    frame = build_altaz_frame(LAT, LON)
    x, y = grid_to_shadow_xy(dl, frame, plumb_length=1.0)
    assert x.shape == dl.shape
    assert y.shape == dl.shape


def test_grid_to_shadow_xy_returns_finite_when_sun_is_up(grids):
    dl, _ = grids
    frame = build_altaz_frame(LAT, LON)
    x, y = grid_to_shadow_xy(dl, frame, plumb_length=1.0)
    # At least a large fraction of points should be finite (sun above horizon)
    finite_frac = np.mean(np.isfinite(x) & np.isfinite(y))
    assert finite_frac > 0.5


def test_plumb_length_scales_shadow_linearly(grids):
    dl, _ = grids
    frame = build_altaz_frame(LAT, LON)
    x1, y1 = grid_to_shadow_xy(dl, frame, plumb_length=1.0)
    x2, y2 = grid_to_shadow_xy(dl, frame, plumb_length=2.0)

    mask = np.isfinite(x1) & np.isfinite(x2) & (np.abs(x1) > 1e-6)
    np.testing.assert_allclose(x2[mask] / x1[mask], 2.0, rtol=1e-6)

    mask_y = np.isfinite(y1) & np.isfinite(y2) & (np.abs(y1) > 1e-6)
    np.testing.assert_allclose(y2[mask_y] / y1[mask_y], 2.0, rtol=1e-6)


def test_compute_blocks_returns_two_lists_of_arrays(grids):
    dl, hl = grids
    blocks_x, blocks_y = compute_blocks(dl, hl, lat=LAT, lon=LON, plumb_length=1.0)

    assert isinstance(blocks_x, list)
    assert isinstance(blocks_y, list)
    assert len(blocks_x) == 2
    assert len(blocks_y) == 2

    assert blocks_x[0].shape == dl.shape
    assert blocks_y[0].shape == dl.shape
    assert blocks_x[1].shape == hl.shape
    assert blocks_y[1].shape == hl.shape
