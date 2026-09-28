import numpy as np

from accuratum.core.plot import Polyline
from accuratum.defaults.labels import select_dayline_labels, select_hourline_labels


def _dayline(date: str) -> Polyline:
    return Polyline(
        kind="dayline",
        xs=np.zeros(2),
        ys=np.zeros(2),
        metadata={"kind": "dayline", "date": date},
    )


def _hourline(hour: int, minute_offset: int) -> Polyline:
    return Polyline(
        kind="hourline",
        xs=np.zeros(2),
        ys=np.zeros(2),
        metadata={"kind": "hourline", "hour": hour, "minute_offset": minute_offset},
    )


# --- dayline selectors -------------------------------------------------------


def test_dayline_one_label_per_month_transition():
    polys = [
        _dayline("2026-01-05"),
        _dayline("2026-01-20"),
        _dayline("2026-02-03"),
        _dayline("2026-03-01"),
    ]
    assert select_dayline_labels(polys) == ["01/05", None, "02/03", "03/01"]


def test_dayline_skips_non_dayline_rows():
    polys = [
        _dayline("2026-01-05"),
        _hourline(6, 0),
        _dayline("2026-02-03"),
    ]
    assert select_dayline_labels(polys) == ["01/05", None, "02/03"]


def test_dayline_handles_year_rollover():
    # Note: the rule is "month differs from last", not "month is later".
    # A wrap from Dec to Jan should still produce a new label.
    polys = [
        _dayline("2025-12-21"),
        _dayline("2025-12-28"),
        _dayline("2026-01-04"),
    ]
    assert select_dayline_labels(polys) == ["12/21", None, "01/04"]


# --- hourline selectors ------------------------------------------------------


def test_hourline_on_the_hour_only():
    polys = [
        _hourline(9, 0),
        _hourline(9, 20),
        _hourline(9, -20),
        _hourline(10, 0),
    ]
    assert select_hourline_labels(polys, time_step_minutes=20) == ["09h", None, None, "10h"]


def test_hourline_within_half_step_tolerance():
    # tolerance = 10 minutes for time_step=20
    polys = [
        _hourline(9, 10),  # exactly at boundary → included
        _hourline(9, 11),  # outside → excluded
        _hourline(9, -10),  # boundary other side → included
    ]
    assert select_hourline_labels(polys, time_step_minutes=20) == ["09h", None, "09h"]


def test_hourline_skips_non_hourline_rows():
    polys = [
        _dayline("2026-01-05"),
        _hourline(6, 0),
    ]
    assert select_hourline_labels(polys, time_step_minutes=20) == [None, "06h"]
