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


def _outline(width: float, height: float, title: str = "", subtitle: str = "") -> Plot:
    xs = np.array([-width / 2, width / 2, width / 2, -width / 2])
    ys = np.array([-height / 2, -height / 2, height / 2, height / 2])
    return Plot(
        polylines=[Polyline("dayline", xs, ys, {"kind": "dayline"})],
        labels=[],
        data_extent=max(width, height),
        title=title,
        subtitle=subtitle,
    )


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
    hints = RenderHints()
    fig, ax = render(_outline(12.0, 5.0, "Planaltina", "2025-12-21 / 2026-06-21"), hints)
    texts = {t.get_text(): t for t in fig.texts}
    title, subtitle = texts["Planaltina"], texts["2025-12-21 / 2026-06-21"]
    left, bottom, width, height = hints.axes_rect
    assert subtitle.get_position()[1] > bottom + height
    assert title.get_position()[1] > subtitle.get_position()[1]


def test_empty_title_means_no_text():
    fig, ax = render(_outline(12.0, 5.0))
    assert not fig.texts


def test_daylines_and_hourlines_take_their_own_colors():
    plot = Plot(
        polylines=[
            Polyline("dayline", np.array([0.0, 1.0]), np.array([0.0, 0.0]), {"kind": "dayline"}),
            Polyline("hourline", np.array([0.0, 0.0]), np.array([0.0, 1.0]), {"kind": "hourline"}),
        ],
        labels=[],
        data_extent=1.0,
    )
    fig, ax = render(plot, RenderHints(dayline_color="#d55e00", hourline_color="#0072b2"))
    assert [line.get_color() for line in ax.lines] == ["#d55e00", "#0072b2"]


def test_render_leaves_pyplot_alone_and_saves_without_it():
    # pyplot's global figure list isn't thread-safe; the website renders in parallel threads.
    import io

    import matplotlib.pyplot as plt

    before = plt.get_fignums()
    fig, _ = render(_outline(12.0, 5.0, title="T"))
    assert plt.get_fignums() == before
    for fmt, magic in (("png", b"\x89PNG"), ("pdf", b"%PDF"), ("svg", b"<?xml")):
        buf = io.BytesIO()
        fig.savefig(buf, format=fmt)
        assert buf.getvalue().startswith(magic)


# --- title and subtitle fit between the overlays -----------------------------


def _hints_with_default_overlays() -> RenderHints:
    from dataclasses import replace

    from accuratum.defaults.overlays import default_render_hints, resolve_image_path

    hints = default_render_hints()
    return replace(hints, overlays=[replace(o, image_path=resolve_image_path(o.image_path)) for o in hints.overlays])


def _header_texts(fig):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    return {t.get_text(): (t, t.get_window_extent(renderer).transformed(fig.transFigure.inverted())) for t in fig.texts}


LONG_TITLE = "Universidade de Brasília - Campus UnB Ceilândia, Distrito Federal"


def test_a_long_title_shrinks_to_fit_between_the_overlays():
    hints = _hints_with_default_overlays()
    fig, _ = render(_outline(12.0, 5.0, LONG_TITLE, "2025-12-21 / 2026-06-21"), hints)
    texts = _header_texts(fig)
    title, box = texts[LONG_TITLE]
    logo = next(o for o in hints.overlays if o.name == "logo").rect
    compass = next(o for o in hints.overlays if o.name == "compass").rect
    assert box.x0 >= logo[0] + logo[2]
    assert box.x1 <= compass[0]
    assert title.get_fontsize() < hints.title_fontsize


def test_the_subtitle_shrinks_in_the_same_proportion():
    hints = _hints_with_default_overlays()
    fig, _ = render(_outline(12.0, 5.0, LONG_TITLE, "2025-12-21 / 2026-06-21"), hints)
    texts = _header_texts(fig)
    title, subtitle = texts[LONG_TITLE][0], texts["2025-12-21 / 2026-06-21"][0]
    assert title.get_fontsize() / hints.title_fontsize == pytest.approx(
        subtitle.get_fontsize() / hints.subtitle_fontsize
    )


def test_a_short_title_keeps_its_size():
    hints = _hints_with_default_overlays()
    fig, _ = render(_outline(12.0, 5.0, "Planaltina", "2025-12-21 / 2026-06-21"), hints)
    sizes = sorted(t.get_fontsize() for t in fig.texts)
    assert sizes == [hints.subtitle_fontsize, hints.title_fontsize]
