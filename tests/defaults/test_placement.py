import numpy as np

from accuratum.core.plot import Polyline
from accuratum.defaults.placement import place_labels


def _dayline(date: str, xs: list[float], ys: list[float]) -> Polyline:
    return Polyline(
        kind="dayline",
        xs=np.array(xs),
        ys=np.array(ys),
        metadata={"kind": "dayline", "date": date},
    )


def _hourline(hour: int, xs: list[float], ys: list[float], offset: int = 0) -> Polyline:
    return Polyline(
        kind="hourline",
        xs=np.array(xs),
        ys=np.array(ys),
        metadata={"kind": "hourline", "hour": hour, "minute_offset": offset},
    )


# --- placement: positions and alignments ------------------------------------


def test_dayline_label_at_both_endpoints_with_correct_alignment():
    # Distinct y at endpoints so the 1-D y collision check doesn't suppress one.
    polys = [_dayline("2026-01-15", xs=[-5.0, 0.0, 5.0], ys=[0.5, 0.0, 2.0])]
    labels = place_labels(
        polys,
        dayline_labels=["01/15"],
        hourline_labels=[None],
        data_extent=10.0,
    )
    assert len(labels) == 2
    left, right = labels
    assert left.x == -5.0 and left.ha == "right" and left.text == "01/15"
    assert right.x == 5.0 and right.ha == "left" and right.text == "01/15"
    assert left.selector == {"kind": "dayline", "date": "2026-01-15", "end": "start"}
    assert right.selector == {"kind": "dayline", "date": "2026-01-15", "end": "end"}


def test_hourline_label_above_first_below_last():
    polys = [_hourline(7, xs=[-3.0, 0.0, 3.0], ys=[2.0, 0.0, -2.0])]
    labels = place_labels(
        polys,
        dayline_labels=[None],
        hourline_labels=["07h"],
        data_extent=10.0,
    )
    assert len(labels) == 2
    first, last = labels
    assert first.y == 2.0 and first.va == "top" and first.text == "07h"
    assert last.y == -2.0 and last.va == "bottom" and last.text == "07h"
    assert first.selector == {"kind": "hourline", "hour": 7, "end": "start"}
    assert last.selector == {"kind": "hourline", "hour": 7, "end": "end"}


# --- collision suppression --------------------------------------------------


def test_hour_label_yields_to_day_label_on_collision():
    # Dayline has distinct y at endpoints so both day labels survive; then a
    # hourline whose endpoints share x with each dayline endpoint must be
    # suppressed entirely (1-D x check against shared placed list).
    polys = [
        _dayline("2026-01-15", xs=[-5.0, 5.0], ys=[0.5, 2.0]),
        _hourline(7, xs=[-5.0, 5.0], ys=[3.0, 3.0]),
    ]
    labels = place_labels(
        polys,
        dayline_labels=["01/15", None],
        hourline_labels=[None, "07h"],
        data_extent=10.0,
    )
    visible = [lbl.text for lbl in labels if not lbl.hidden]
    assert visible.count("01/15") == 2
    assert "07h" not in visible


def test_dayline_collision_uses_y_axis_only():
    # Two daylines whose endpoints sit at very different x but identical y →
    # second should be suppressed (1-D y check).
    polys = [
        _dayline("2026-01-15", xs=[-5.0, 5.0], ys=[1.0, 1.0]),
        _dayline("2026-02-01", xs=[-4.0, 4.0], ys=[1.0, 1.0]),  # same y
    ]
    labels = place_labels(
        polys,
        dayline_labels=["01/15", "02/01"],
        hourline_labels=[None, None],
        data_extent=10.0,
    )
    assert {lbl.text for lbl in labels if not lbl.hidden} == {"01/15"}


def test_plumb_exclusion_drops_hour_labels_near_origin():
    polys = [
        _hourline(12, xs=[0.1, 0.1], ys=[0.1, 0.1]),  # well inside default 0.12*10 = 1.2 disk
        _hourline(7, xs=[-5.0, 5.0], ys=[2.0, 2.0]),  # far from origin
    ]
    labels = place_labels(
        polys,
        dayline_labels=[None, None],
        hourline_labels=["12h", "07h"],
        data_extent=10.0,
    )
    visible = {lbl.text for lbl in labels if not lbl.hidden}
    assert "12h" not in visible
    assert "07h" in visible


# --- suppressed labels are kept, hidden ----------------------------------------


def test_suppressed_labels_are_kept_as_hidden():
    # Suppression hides a label instead of dropping it, so a human can restore
    # it by flipping ``hidden`` in the project file.
    polys = [
        _hourline(12, xs=[0.1, 0.1], ys=[0.1, 0.1]),
        _hourline(7, xs=[-5.0, 5.0], ys=[2.0, 2.0]),
    ]
    labels = place_labels(
        polys,
        dayline_labels=[None, None],
        hourline_labels=["12h", "07h"],
        data_extent=10.0,
    )
    noon = [lbl for lbl in labels if lbl.text == "12h"]
    assert len(noon) == 2
    assert all(lbl.hidden for lbl in noon)
    assert not any(lbl.hidden for lbl in labels if lbl.text == "07h")


def test_hidden_labels_do_not_block_later_labels():
    # A hidden label must not count as placed in the collision check.
    polys = [
        _hourline(12, xs=[0.1, 0.1], ys=[0.1, 0.1]),  # hidden by plumb exclusion
        _hourline(13, xs=[0.1, 0.1], ys=[5.0, -5.0]),  # same x, outside the disk
    ]
    labels = place_labels(
        polys,
        dayline_labels=[None, None],
        hourline_labels=["12h", "13h"],
        data_extent=10.0,
    )
    assert [lbl.hidden for lbl in labels if lbl.text == "13h"] == [False, True]


def test_every_label_has_a_unique_selector():
    polys = [
        _dayline("2026-01-15", xs=[-5.0, 5.0], ys=[1.0, 1.0]),
        _hourline(7, xs=[-3.0, 3.0], ys=[2.0, -2.0]),
    ]
    labels = place_labels(
        polys,
        dayline_labels=["01/15", None],
        hourline_labels=[None, "07h"],
        data_extent=10.0,
    )
    keys = [tuple(sorted(lbl.selector.items())) for lbl in labels]
    assert len(keys) == 4
    assert len(set(keys)) == 4
