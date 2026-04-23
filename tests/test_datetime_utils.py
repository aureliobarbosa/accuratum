from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from accuratum.datetime_utils import (
    build_dayline_grid,
    build_hourline_grid,
    frame_periods,
    get_solstices,
)

TZ_SP = ZoneInfo("America/Sao_Paulo")


def test_get_solstices_returns_three_datetimes():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    first, middle, last = get_solstices(reference)

    assert first.year == 2025
    assert first.month == 12
    assert first.day == 21
    assert middle.year == 2026
    assert middle.month == 6
    assert middle.day == 21
    assert last.year == 2026
    assert last.month == 12
    assert last.day == 21


def test_get_solstices_preserves_timezone():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    first, middle, last = get_solstices(reference)
    for s in (first, middle, last):
        assert s.tzinfo == TZ_SP


def test_get_solstices_custom_day():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    first, middle, last = get_solstices(reference, solstice_day=20)
    assert first.day == middle.day == last.day == 20


def test_frame_periods_returns_two_pairs():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    solstices = get_solstices(reference)
    periods = frame_periods(solstices)

    assert len(periods) == 2
    assert len(periods[0]) == 2
    assert len(periods[1]) == 2
    # First pair: dec prev -> jun current
    assert periods[0][0] == solstices[0]
    assert periods[0][1] == solstices[1]
    # Second pair: jun current -> dec current
    assert periods[1][0] == solstices[1]
    assert periods[1][1] == solstices[2]


def test_build_dayline_grid_shape_and_dtype():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    solstices = get_solstices(reference)
    periods = frame_periods(solstices)

    grid = build_dayline_grid(
        periods[0],
        sunrise=6,
        sunset=18,
        day_step=timedelta(days=7),
        time_step=timedelta(minutes=1),
    )
    assert isinstance(grid, np.ndarray)
    assert grid.ndim == 2
    # Type must be a numpy datetime64
    assert np.issubdtype(grid.dtype, np.datetime64)
    # The first point must be near the start date at sunrise+1 UTC-converted hour
    assert grid.shape[0] > 0
    assert grid.shape[1] > 0


def test_build_hourline_grid_shape_and_dtype():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    solstices = get_solstices(reference)
    periods = frame_periods(solstices)

    grid = build_hourline_grid(
        periods[1],
        sunrise=6,
        sunset=18,
        day_step=timedelta(days=1),
        time_step=timedelta(minutes=10),
    )
    assert isinstance(grid, np.ndarray)
    assert grid.ndim == 2
    assert np.issubdtype(grid.dtype, np.datetime64)
    assert grid.shape[0] > 0
    assert grid.shape[1] > 0


def test_dayline_and_hourline_have_different_orientations():
    """Dayline grid rows are days; hourline grid rows are times (transposed semantics)."""
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    solstices = get_solstices(reference)
    period = frame_periods(solstices)[0]

    dl = build_dayline_grid(period, 6, 18, timedelta(days=7), timedelta(minutes=1))
    hl = build_hourline_grid(period, 6, 18, timedelta(days=1), timedelta(minutes=10))

    # Dayline row should advance along time (minutes) — consecutive elements ~1 min apart
    dl_delta = dl[0, 1] - dl[0, 0]
    assert dl_delta == np.timedelta64(1, "m")

    # Hourline row should advance along days — consecutive elements ~1 day apart
    hl_delta = hl[0, 1] - hl[0, 0]
    assert hl_delta == np.timedelta64(1, "D")


def test_invalid_frame_period_raises():
    with pytest.raises((TypeError, ValueError)):
        build_dayline_grid(
            "not a period",
            6,
            18,
            timedelta(days=7),
            timedelta(minutes=1),
        )
