from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np

from accuratum.core.spec import GridConfig, Location, TimeFrame
from accuratum.core.timegrid import dayline_grid, hourline_grid

TZ_SP = ZoneInfo("America/Sao_Paulo")
PLANALTINA = Location(lat=-15.6006489, lon=-47.6580608, timezone="America/Sao_Paulo")
TIMEFRAME = TimeFrame(
    start=datetime(2025, 12, 21, tzinfo=TZ_SP),
    end=datetime(2026, 6, 21, tzinfo=TZ_SP),
)
# Coarse grid for fast tests
FAST_GRID = GridConfig(
    dayline_day_step_days=30,
    line_points=20,
    hourline_day_step_days=30,
    time_step_minutes=120,
    horizon_degrees=10.0,
)


def test_dayline_grid_shape_and_dtype():
    grid = dayline_grid(TIMEFRAME, PLANALTINA, FAST_GRID)
    assert grid.dtype == np.dtype("datetime64[s]")
    assert grid.shape[1] == FAST_GRID.line_points
    assert grid.shape[0] > 0


def test_dayline_grid_rows_are_strictly_increasing():
    grid = dayline_grid(TIMEFRAME, PLANALTINA, FAST_GRID)
    diffs = np.diff(grid.astype(np.int64), axis=1)
    assert np.all(diffs > 0)


def test_hourline_grid_shape_and_dtype():
    grid = hourline_grid(TIMEFRAME, PLANALTINA, FAST_GRID)
    assert grid.dtype == np.dtype("datetime64[s]")
    assert grid.shape[0] > 0
    assert grid.shape[1] > 0


def test_hourline_grid_masks_out_of_window_with_nat():
    grid = hourline_grid(TIMEFRAME, PLANALTINA, FAST_GRID)
    assert np.isnat(grid).any()
