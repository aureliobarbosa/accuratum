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
    assert left.x <= -5.0 and left.ha == "right" and left.text == "01/15"
    assert right.x >= 5.0 and right.ha == "left" and right.text == "01/15"
    assert left.selector == {"kind": "dayline", "date": "2026-01-15", "end": "start"}
    assert right.selector == {"kind": "dayline", "date": "2026-01-15", "end": "end"}


def test_hourline_labels_point_outward_on_a_line_running_up():
    # Dec→Jun frame: the first sample is the lower end. Its label goes below
    # it (va="top"), the last one above (va="bottom").
    polys = [_hourline(7, xs=[-3.0, 0.0, 3.0], ys=[-2.0, 0.0, 2.0])]
    labels = place_labels(polys, dayline_labels=[None], hourline_labels=["07h"], data_extent=10.0)
    assert len(labels) == 2
    first, last = labels
    assert first.y <= -2.0 and first.va == "top" and first.text == "07h"
    assert last.y >= 2.0 and last.va == "bottom" and last.text == "07h"
    assert first.selector == {"kind": "hourline", "hour": 7, "end": "start"}
    assert last.selector == {"kind": "hourline", "hour": 7, "end": "end"}


def test_hourline_labels_point_outward_on_a_line_running_down():
    # Jun→Dec frame (issue #4): the first sample is the upper end. A label
    # below it would sit on the drawing, so it goes above, and the last
    # (lower) one goes below.
    polys = [_hourline(7, xs=[-3.0, 0.0, 3.0], ys=[2.0, 0.0, -2.0])]
    labels = place_labels(polys, dayline_labels=[None], hourline_labels=["07h"], data_extent=10.0)
    first, last = labels
    assert first.y >= 2.0 and first.va == "bottom"
    assert last.y <= -2.0 and last.va == "top"
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


def test_day_label_does_not_collide_with_its_own_twin():
    # A dayline's endpoints sit at almost the same y. The left and right labels
    # are on opposite sides, so they must not suppress each other (Step 3 bug).
    polys = [_dayline("2026-01-15", xs=[-5.0, 0.0, 5.0], ys=[1.0, 0.0, 1.01])]
    labels = place_labels(polys, dayline_labels=["01/15"], hourline_labels=[None], data_extent=10.0)
    assert [lbl.hidden for lbl in labels] == [False, False]


def test_hour_label_does_not_collide_with_its_own_twin():
    # Same bug for hourlines: the labels below and above share x but not a side.
    polys = [_hourline(16, xs=[1.4, 1.2], ys=[-0.5, 1.0])]
    labels = place_labels(polys, dayline_labels=[None], hourline_labels=["16h"], data_extent=10.0)
    assert [lbl.hidden for lbl in labels] == [False, False]


def test_hour_labels_collide_only_on_the_same_side():
    # 16h's bottom label is 0.2 from 15h's top label in x (under the 0.4
    # tolerance) but on the other side, so it stays; its top label is 0.2
    # from 15h's top label and is hidden.
    polys = [
        _hourline(15, xs=[0.9, 1.2], ys=[-0.3, 1.0]),
        _hourline(16, xs=[1.4, 1.4], ys=[-0.5, 1.5]),
    ]
    labels = place_labels(polys, dayline_labels=[None, None], hourline_labels=["15h", "16h"], data_extent=10.0)
    assert [lbl.hidden for lbl in labels if lbl.text == "16h"] == [False, True]


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
    assert [lbl.hidden for lbl in labels if lbl.text == "13h"] == [False, False]


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


def test_hour_labels_collide_by_side_not_by_end():
    # 15h runs up and 16h runs down, so their top labels come from different
    # ends. They share a side and sit 0.2 apart in x, so 16h's top is hidden.
    polys = [
        _hourline(15, xs=[0.9, 1.2], ys=[-0.3, 1.0]),
        _hourline(16, xs=[1.4, 3.0], ys=[1.5, -0.5]),
    ]
    labels = place_labels(polys, dayline_labels=[None, None], hourline_labels=["15h", "16h"], data_extent=10.0)
    sixteen = [(lbl.va, lbl.hidden) for lbl in labels if lbl.text == "16h"]
    assert sixteen == [("bottom", True), ("top", False)]


# --- text boxes: clear of lines and of each other (issue #4 follow-up) -------

EM = 0.1  # one em of label text in data units


def test_hour_label_clears_a_slanted_line_through_its_endpoint():
    # The lower end of 10h sits on a solstice line with slope 0.8. A label
    # hung right at the endpoint would cut the line with one corner.
    polys = [
        _dayline("2026-06-21", xs=[-3.0, 3.0], ys=[-2.4, 2.4]),
        _hourline(10, xs=[0.0, 0.0], ys=[0.0, 3.0]),
    ]
    labels = place_labels(polys, [None, None], [None, "10h"], data_extent=1.0, em=EM)
    lower = labels[0]
    half_width = 1.93 * EM / 2
    assert lower.va == "top" and lower.x == 0.0
    assert lower.y < -0.8 * half_width  # the box's top edge is below the line at its corner


def test_day_label_clears_a_neighbouring_line_that_sticks_out():
    # 06/21's left label would cover the end of the line below it, which
    # starts further left; it moves left until it is clear.
    polys = [
        _dayline("2026-06-21", xs=[-5.0, 5.0], ys=[0.0, 0.0]),
        _dayline("2026-06-22", xs=[-5.1, 5.0], ys=[0.03, 0.03]),
    ]
    labels = place_labels(polys, ["06/21", None], [None, None], data_extent=10.0, em=EM)
    left = labels[0]
    assert left.ha == "right" and not left.hidden
    assert left.x < -5.1


def test_hour_label_hides_when_its_text_overlaps_a_day_label():
    # 12/21 is anchored at its right edge and extends left, over 11h's lower
    # label (Edinburgh). The anchors are 0.15 apart in x, past the 0.04
    # tolerance, so only the text boxes show the overlap.
    polys = [
        _dayline("2026-12-21", xs=[0.0, 1.0], ys=[0.0, 0.0]),
        _hourline(11, xs=[-0.15, -0.15], ys=[0.06, 1.0]),
    ]
    labels = place_labels(polys, ["12/21", None], [None, "11h"], data_extent=1.0, em=EM)
    eleven = [(lbl.va, lbl.hidden) for lbl in labels if lbl.text == "11h"]
    assert eleven == [("top", True), ("bottom", False)]


def test_label_falls_back_to_where_its_line_would_continue():
    # 06h ends on a steep solstice curve, flanked above and below by the
    # neighbouring hour lines (Reykjavik). Up and down are blocked; past the
    # end of its own line (to the right, inside the dial) is free.
    polys = [
        _dayline("2026-06-21", xs=[0.0, 0.0], ys=[-1.0, 1.0]),
        _hourline(5, xs=[-1.0, 0.0], ys=[0.1, 0.1]),
        _hourline(6, xs=[-1.0, 0.0], ys=[0.0, 0.0]),
        _hourline(7, xs=[-1.0, 0.0], ys=[-0.1, -0.1]),
    ]
    labels = place_labels(polys, [None] * 4, [None, None, "06h", None], data_extent=10.0, em=EM, plumb_exclusion=0.0)
    end = next(lbl for lbl in labels if lbl.selector["end"] == "end")
    assert not end.hidden
    assert end.ha == "left" and end.va == "center" and end.x > 0.0
