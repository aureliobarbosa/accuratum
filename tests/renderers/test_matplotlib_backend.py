"""Structural tests for the matplotlib renderer. The look is checked visually."""

import numpy as np
import pytest

from accuratum.core.hints import RenderHints
from accuratum.core.plot import Label, Plot, Polyline
from accuratum.renderers.matplotlib_backend import render


def test_hidden_labels_are_not_drawn():
    plot = Plot(
        polylines=[
            Polyline(
                kind="hourline",
                xs=np.array([-3.0, 3.0]),
                ys=np.array([2.0, -2.0]),
                metadata={"kind": "hourline", "hour": 7, "minute_offset": 0},
            )
        ],
        labels=[
            Label(text="shown", x=-3.0, y=2.0, ha="center", va="top", kind="hourline"),
            Label(text="gone", x=3.0, y=-2.0, ha="center", va="bottom", kind="hourline", hidden=True),
        ],
        data_extent=6.0,
    )
    fig, ax = render(plot)
    texts = [t.get_text() for t in ax.texts]
    assert "shown" in texts
    assert "gone" not in texts


def _outline(width: float, height: float) -> Plot:
    xs = np.array([-width / 2, width / 2, width / 2, -width / 2])
    ys = np.array([-height / 2, -height / 2, height / 2, height / 2])
    return Plot(polylines=[Polyline("dayline", xs, ys, {"kind": "dayline"})], labels=[], data_extent=max(width, height))


@pytest.mark.parametrize("width, height", [(12.0, 5.0), (12.0, 11.0), (4.0, 11.0)])
def test_drawing_stays_in_axes_rect_pinned_to_its_top(width, height):
    """Wide (low latitude) or tall (high latitude), the drawing never climbs
    into the header band above ``axes_rect``, where the overlays go."""
    hints = RenderHints(axes_rect=(0.05, 0.05, 0.9, 0.7))
    fig, ax = render(_outline(width, height), hints)
    fig.canvas.draw()
    box = ax.get_position()
    left, bottom, w, h = hints.axes_rect
    assert box.y1 == pytest.approx(bottom + h)
    assert box.x0 >= left - 1e-9 and box.x1 <= left + w + 1e-9 and box.y0 >= bottom - 1e-9


def test_no_frame_around_the_drawing():
    fig, ax = render(_outline(12.0, 5.0))
    assert not any(spine.get_visible() for spine in ax.spines.values())


def test_title_and_subtitle_sit_in_the_header_band():
    hints = RenderHints(title="Planaltina", subtitle="2025-12-21 / 2026-06-21")
    fig, ax = render(_outline(12.0, 5.0), hints)
    texts = {t.get_text(): t for t in fig.texts}
    title, subtitle = texts["Planaltina"], texts["2025-12-21 / 2026-06-21"]
    left, bottom, width, height = hints.axes_rect
    assert subtitle.get_position()[1] > bottom + height
    assert title.get_position()[1] > subtitle.get_position()[1]


@pytest.mark.parametrize("title", [None, ""])
def test_no_title_means_no_text(title):
    fig, ax = render(_outline(12.0, 5.0), RenderHints(title=title, subtitle=title))
    assert not fig.texts
