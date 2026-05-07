from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from astropy.coordinates import AltAz

from accuratum.astronomy import (
    build_altaz_frame,
    compute_blocks,
    dayline_grid,
    get_sunrises_and_sunsets,
    grid_to_shadow_xy,
    hourline_grid,
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
    xs, ys = grid_to_shadow_xy(dl, frame, plumb_length=1.0)
    assert isinstance(xs, list) and isinstance(ys, list)
    assert len(xs) == dl.shape[0]
    assert len(ys) == dl.shape[0]
    for x_row, y_row in zip(xs, ys):
        assert x_row.shape == (dl.shape[1],)
        assert y_row.shape == (dl.shape[1],)


def test_grid_to_shadow_xy_returns_finite_when_sun_is_up(grids):
    dl, _ = grids
    frame = build_altaz_frame(LAT, LON)
    xs, ys = grid_to_shadow_xy(dl, frame, plumb_length=1.0)
    x = np.concatenate(xs)
    y = np.concatenate(ys)
    # At least a large fraction of points should be finite (sun above horizon)
    finite_frac = np.mean(np.isfinite(x) & np.isfinite(y))
    assert finite_frac > 0.5


def test_plumb_length_scales_shadow_linearly(grids):
    dl, _ = grids
    frame = build_altaz_frame(LAT, LON)
    xs1, ys1 = grid_to_shadow_xy(dl, frame, plumb_length=1.0)
    xs2, ys2 = grid_to_shadow_xy(dl, frame, plumb_length=2.0)
    x1 = np.concatenate(xs1)
    y1 = np.concatenate(ys1)
    x2 = np.concatenate(xs2)
    y2 = np.concatenate(ys2)

    mask = np.isfinite(x1) & np.isfinite(x2) & (np.abs(x1) > 1e-6)
    np.testing.assert_allclose(x2[mask] / x1[mask], 2.0, rtol=1e-6)

    mask_y = np.isfinite(y1) & np.isfinite(y2) & (np.abs(y1) > 1e-6)
    np.testing.assert_allclose(y2[mask_y] / y1[mask_y], 2.0, rtol=1e-6)


def test_grid_to_shadow_xy_skips_nat_per_line():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    solstices = get_solstices(reference)
    period = frame_periods(solstices)[0]
    grid = hourline_grid(period, lat=LAT, lon=LON, day_step=timedelta(days=1), time_step=timedelta(minutes=20))
    assert np.isnat(grid).any()  # sanity: this grid does contain NaT entries

    frame = build_altaz_frame(LAT, LON)
    xs, ys = grid_to_shadow_xy(grid, frame, plumb_length=1.0)

    assert isinstance(xs, list) and isinstance(ys, list)
    assert len(xs) == grid.shape[0]
    assert len(ys) == grid.shape[0]

    for i, (x_row, y_row) in enumerate(zip(xs, ys)):
        expected_len = int(np.sum(~np.isnat(grid[i])))
        assert x_row.ndim == 1 and y_row.ndim == 1
        assert x_row.shape == (expected_len,)
        assert y_row.shape == (expected_len,)
        assert np.all(np.isfinite(x_row))
        assert np.all(np.isfinite(y_row))


@pytest.fixture(scope="module")
def sun_times():
    days = np.array(["2026-06-21", "2026-09-21", "2026-12-21"], dtype="datetime64[D]")
    rises, sets = get_sunrises_and_sunsets(days, lat=LAT, lon=LON)
    return rises, sets


def test_get_sunrises_and_sunsets_shape(sun_times):
    rises, sets = sun_times
    assert rises.shape == (3,)
    assert sets.shape == (3,)


def test_get_sunrises_and_sunsets_dtype(sun_times):
    rises, sets = sun_times
    assert rises.dtype == np.dtype("datetime64[s]")
    assert sets.dtype == np.dtype("datetime64[s]")


def test_get_sunrises_and_sunsets_sunset_after_sunrise(sun_times):
    rises, sets = sun_times
    assert np.all(sets.astype(np.int64) > rises.astype(np.int64))


def test_get_sunrises_and_sunsets_horizon_shifts_times(sun_times):
    rises_0, sets_0 = sun_times
    days = np.array(["2026-06-21", "2026-09-21", "2026-12-21"], dtype="datetime64[D]")
    rises_10, sets_10 = get_sunrises_and_sunsets(days, lat=LAT, lon=LON, horizon=10.0)
    # 10° horizon → later sunrise, earlier sunset
    assert np.all(rises_10.astype(np.int64) > rises_0.astype(np.int64))
    assert np.all(sets_10.astype(np.int64) < sets_0.astype(np.int64))


@pytest.fixture(scope="module")
def dl_grid():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    solstices = get_solstices(reference)
    period = frame_periods(solstices)[0]
    return dayline_grid(period, lat=LAT, lon=LON, day_step=timedelta(days=7), line_points=500)


def test_dayline_grid_shape(dl_grid):
    n_days, n_points = dl_grid.shape
    assert n_points == 500
    assert n_days > 0


def test_dayline_grid_dtype(dl_grid):
    assert dl_grid.dtype == np.dtype("datetime64[s]")


def test_dayline_grid_rows_are_ordered(dl_grid):
    # Each row must be strictly increasing in time
    diffs = np.diff(dl_grid.astype(np.int64), axis=1)
    assert np.all(diffs > 0)


def test_dayline_grid_day_window_is_positive(dl_grid):
    # Each row must span a positive duration (sunset > sunrise)
    spans = dl_grid[:, -1].astype(np.int64) - dl_grid[:, 0].astype(np.int64)
    assert np.all(spans > 0)


def test_dayline_grid_hours_are_daytime(dl_grid):
    # At Brasília (-15°), all start times should be between 06:00 and 12:00 UTC
    # and end times between 12:00 and 22:00 UTC — a loose sanity check
    hours_start = dl_grid[:, 0].astype("datetime64[h]").astype(np.int64) % 24
    hours_end = dl_grid[:, -1].astype("datetime64[h]").astype(np.int64) % 24
    assert np.all(hours_start >= 6) and np.all(hours_start <= 12)
    assert np.all(hours_end >= 14) and np.all(hours_end <= 22)


@pytest.fixture(scope="module")
def hl_grid():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    solstices = get_solstices(reference)
    period = frame_periods(solstices)[0]
    return hourline_grid(period, lat=LAT, lon=LON, day_step=timedelta(days=1), time_step=timedelta(minutes=20))


def test_hourline_grid_shape(hl_grid):
    n_times, n_days = hl_grid.shape
    assert n_times > 0
    assert n_days > 0


def test_hourline_grid_dtype(hl_grid):
    assert hl_grid.dtype == np.dtype("datetime64[s]")


def test_hourline_grid_has_some_nat(hl_grid):
    # By design, sub-horizon (10°) moments are NaT — at solstices the day
    # length differs enough that some cells are masked.
    assert np.isnat(hl_grid).any()


def test_hourline_grid_columns_are_ordered(hl_grid):
    # Each column = one day, time increasing down rows. NaT entries are
    # excluded from the monotonicity check.
    for j in range(hl_grid.shape[1]):
        col = hl_grid[:, j]
        valid = col[~np.isnat(col)]
        if valid.size < 2:
            continue
        diffs = np.diff(valid.astype(np.int64))
        assert np.all(diffs > 0), f"column {j} not strictly increasing"


def test_hourline_grid_rows_are_ordered(hl_grid):
    # Each row = approximately constant clock time, day increasing across
    # columns. NaT entries are excluded.
    for i in range(hl_grid.shape[0]):
        row = hl_grid[i, :]
        valid = row[~np.isnat(row)]
        if valid.size < 2:
            continue
        diffs = np.diff(valid.astype(np.int64))
        assert np.all(diffs > 0), f"row {i} not strictly increasing"


def test_hourline_grid_nonnat_values_are_within_sunrise_sunset(hl_grid):
    # Every non-NaT value must lie inside that day's [sunrise, sunset] window
    # at the same horizon used by the grid (10°).
    days = hl_grid[0, :].astype("datetime64[D]")
    # First row may itself be NaT for some columns; fall back to the grid's
    # day axis directly via column-wise min/max.
    valid_per_col = [hl_grid[:, j][~np.isnat(hl_grid[:, j])] for j in range(hl_grid.shape[1])]
    days = np.array(
        [v[0].astype("datetime64[D]") if v.size else None for v in valid_per_col],
        dtype=object,
    )
    real_days = np.array([d for d in days if d is not None], dtype="datetime64[D]")
    rises, sets = get_sunrises_and_sunsets(real_days, lat=LAT, lon=LON, horizon=10.0)
    k = 0
    for v in valid_per_col:
        if v.size == 0:
            continue
        assert np.all(v >= rises[k]) and np.all(v <= sets[k])
        k += 1


def test_compute_blocks_returns_two_lists_of_arrays(grids):
    dl, hl = grids
    blocks_x, blocks_y = compute_blocks(dl, hl, lat=LAT, lon=LON, plumb_length=1.0)

    assert isinstance(blocks_x, list)
    assert isinstance(blocks_y, list)
    assert len(blocks_x) == 2
    assert len(blocks_y) == 2

    # Each block is a list of 1-D rows (one polyline per grid row)
    assert len(blocks_x[0]) == dl.shape[0]
    assert len(blocks_y[0]) == dl.shape[0]
    assert len(blocks_x[1]) == hl.shape[0]
    assert len(blocks_y[1]) == hl.shape[0]
    for x_row, y_row in zip(blocks_x[0], blocks_y[0]):
        assert x_row.shape == (dl.shape[1],)
        assert y_row.shape == (dl.shape[1],)
    for x_row, y_row in zip(blocks_x[1], blocks_y[1]):
        assert x_row.shape == (hl.shape[1],)
        assert y_row.shape == (hl.shape[1],)
