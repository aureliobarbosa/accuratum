from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from accuratum.core.builder import build_plot
from accuratum.core.spec import (
    GridConfig,
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


def test_each_label_has_a_unique_selector(plot):
    keys = [tuple(sorted(lbl.selector.items())) for lbl in plot.labels]
    assert len(keys) == len(set(keys))


def test_unsupported_sundial_type_raises():
    spec = SundialSpec(
        location=PLANALTINA,
        timeframe=FAST_FRAME,
        grid=FAST_GRID,
        sundial_type="not-a-real-type",
    )
    with pytest.raises(ValueError):
        build_plot(spec)


# --- daylight saving time -----------------------------------------------------

TZ_LON = ZoneInfo("Europe/London")
EDINBURGH = Location(lat=55.95, lon=-3.19, timezone="Europe/London")


def test_standard_time_ignores_daylight_saving():
    from accuratum.core.builder import _utc_dt64_to_standard_time

    # 29 March 2026 is the switch to BST; both sides read the same standard hour.
    before = _utc_dt64_to_standard_time(np.datetime64("2026-03-25T14:04"), TZ_LON)
    after = _utc_dt64_to_standard_time(np.datetime64("2026-04-03T14:04"), TZ_LON)
    assert (before.hour, before.minute) == (after.hour, after.minute) == (14, 4)


def test_standard_time_keeps_zones_without_dst():
    from accuratum.core.builder import _utc_dt64_to_standard_time

    local = _utc_dt64_to_standard_time(np.datetime64("2026-01-15T15:00"), TZ_SP)
    assert local.hour == 12


def test_hour_lines_are_unique_and_consecutive_across_dst():
    spec = SundialSpec(
        location=EDINBURGH,
        timeframe=TimeFrame(start=datetime(2025, 12, 21, tzinfo=TZ_LON), end=datetime(2026, 6, 21, tzinfo=TZ_LON)),
        grid=GridConfig(
            dayline_day_step_days=30,
            line_points=20,
            hourline_day_step_days=7,
            time_step_minutes=20,
            horizon_degrees=10.0,
        ),
    )
    plot = build_plot(spec)
    hours = [lab.selector["hour"] for lab in plot.labels if lab.kind == "hourline" and lab.selector["end"] == "start"]
    assert len(hours) == len(set(hours))
    assert hours == list(range(hours[0], hours[0] + len(hours)))


@pytest.mark.parametrize("lat", [62.0, -62.0])
@pytest.mark.parametrize("start, end", [((2025, 12, 21), (2026, 6, 21)), ((2026, 6, 21), (2026, 12, 21))])
def test_build_plot_at_the_edges_of_the_latitude_range(lat, start, end):
    """±62° (Ferraz station) has winter days with the sun below the 10° cut."""
    tz = ZoneInfo("UTC")
    spec = SundialSpec(
        location=Location(lat=lat, lon=-58.39, timezone="UTC"),
        timeframe=TimeFrame(start=datetime(*start, tzinfo=tz), end=datetime(*end, tzinfo=tz)),
        grid=GridConfig(dayline_day_step_days=7, line_points=20, hourline_day_step_days=7, time_step_minutes=60),
    )
    plot = build_plot(spec)
    assert {p.kind for p in plot.polylines} == {"dayline", "hourline"}
    for poly in plot.polylines:
        assert poly.xs.size > 0
        assert np.all(np.isfinite(poly.xs)) and np.all(np.isfinite(poly.ys))
    assert any(not label.hidden for label in plot.labels)
