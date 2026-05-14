from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from accuratum.core.builder import build_plot
from accuratum.core.spec import (
    GridConfig,
    LabelOverride,
    Location,
    SundialSpec,
    TimeFrame,
)

TZ_SP = ZoneInfo("America/Sao_Paulo")
PLANALTINA = Location(lat=-15.6006489, lon=-47.6580608, timezone="America/Sao_Paulo")

# Coarse grid for fast tests
FAST_GRID = GridConfig(
    dayline_day_step_days=30,
    line_points=20,
    hourline_day_step_days=30,
    time_step_minutes=120,
    horizon_degrees=10.0,
)
FAST_FRAME = TimeFrame(
    start=datetime(2025, 12, 21, tzinfo=TZ_SP),
    end=datetime(2026, 6, 21, tzinfo=TZ_SP),
)


@pytest.fixture(scope="module")
def plot():
    spec = SundialSpec(
        location=PLANALTINA,
        timeframe=FAST_FRAME,
        plumb_length=1.0,
        grid=FAST_GRID,
    )
    return build_plot(spec)


def test_plot_has_polylines_of_both_kinds(plot):
    kinds = {p.kind for p in plot.polylines}
    assert "dayline" in kinds
    assert "hourline" in kinds


def test_dayline_polylines_carry_date_metadata(plot):
    dl = [p for p in plot.polylines if p.kind == "dayline" and p.xs.size]
    assert dl
    for p in dl:
        assert p.metadata["kind"] == "dayline"
        assert isinstance(p.metadata["date"], str)
        # local-tz YYYY-MM-DD
        datetime.strptime(p.metadata["date"], "%Y-%m-%d")


def test_hourline_polylines_carry_hour_metadata(plot):
    hl = [p for p in plot.polylines if p.kind == "hourline" and p.xs.size]
    assert hl
    for p in hl:
        assert p.metadata["kind"] == "hourline"
        assert 0 <= p.metadata["hour"] < 24
        assert -30 <= p.metadata["minute_offset"] <= 30


def test_plot_produces_some_labels(plot):
    assert len(plot.labels) > 0
    kinds = {lbl.kind for lbl in plot.labels}
    assert "dayline" in kinds or "hourline" in kinds


def test_dayline_labels_are_month_day_format(plot):
    for lbl in plot.labels:
        if lbl.kind == "dayline":
            assert len(lbl.text) == 5 and lbl.text[2] == "/"


def test_hourline_labels_are_hh_h_format(plot):
    for lbl in plot.labels:
        if lbl.kind == "hourline":
            assert lbl.text.endswith("h")
            assert len(lbl.text) == 3


def test_labels_carry_metadata_selectors(plot):
    for lbl in plot.labels:
        assert "kind" in lbl.selector
        if lbl.kind == "dayline":
            assert "date" in lbl.selector
        if lbl.kind == "hourline":
            assert "hour" in lbl.selector


def test_data_extent_is_positive(plot):
    assert plot.data_extent > 0


def test_polylines_have_finite_xy(plot):
    for p in plot.polylines:
        if p.xs.size:
            assert np.all(np.isfinite(p.xs))
            assert np.all(np.isfinite(p.ys))


# --- override application ----------------------------------------------------


def test_override_hide_removes_matching_label():
    # First build without overrides to find an existing label.
    spec_no_ov = SundialSpec(location=PLANALTINA, timeframe=FAST_FRAME, grid=FAST_GRID)
    plot_a = build_plot(spec_no_ov)
    target = next(lbl for lbl in plot_a.labels if lbl.kind == "hourline")

    spec_ov = SundialSpec(
        location=PLANALTINA,
        timeframe=FAST_FRAME,
        grid=FAST_GRID,
        overrides=[LabelOverride(selector=target.selector, hidden=True)],
    )
    plot_b = build_plot(spec_ov)
    assert not any(lbl.selector == target.selector for lbl in plot_b.labels)


def test_unsupported_sundial_type_raises():
    spec = SundialSpec(
        location=PLANALTINA,
        timeframe=FAST_FRAME,
        grid=FAST_GRID,
        sundial_type="not-a-real-type",
    )
    with pytest.raises(ValueError):
        build_plot(spec)
