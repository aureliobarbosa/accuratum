import io
import re

import pytest
from PIL import Image

from accuratum.core.spec import GridConfig
from accuratum_web.sundial import (
    MAX_IMAGE_BYTES,
    MAX_IMAGE_SIDE,
    MAX_TEXT_LENGTH,
    PageTexts,
    SundialRequest,
    build_pages,
    make_sundial,
    sanitize_image,
)

FAST_GRID = GridConfig(dayline_day_step_days=30, line_points=20, hourline_day_step_days=10, time_step_minutes=60)


def _png(width: int = 40, height: int = 20, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (200, 30, 30)).save(buf, format=fmt)
    return buf.getvalue()


def _request(**changes) -> SundialRequest:
    values = dict(
        lat=-15.78,
        lon=-47.92,
        year=2026,
        dayline_color="#d55e00",
        hourline_color="#0072b2",
        pages=(PageTexts("UnB", "dez–jun"), PageTexts("UnB", "jun–dez")),
    )
    values.update(changes)
    return SundialRequest(**values)


# --- the request -------------------------------------------------------------


@pytest.mark.parametrize("color", ["red", "#fff", "#12345g", "#1234567", "rgb(0,0,0)", " #d55e00"])
def test_colors_must_be_rrggbb(color):
    with pytest.raises(ValueError, match="color"):
        _request(dayline_color=color)


def test_texts_are_capped():
    long = "x" * (MAX_TEXT_LENGTH + 1)
    with pytest.raises(ValueError, match="title"):
        _request(pages=(PageTexts(long, ""), PageTexts("", "")))
    with pytest.raises(ValueError, match="subtitle"):
        _request(pages=(PageTexts("", ""), PageTexts("", long)))


def test_exactly_two_pages():
    with pytest.raises(ValueError, match="two pages"):
        _request(pages=(PageTexts("a", "b"),))


# --- the pages ---------------------------------------------------------------


def test_one_page_per_half_year_with_its_own_texts():
    pages = build_pages(_request(), grid=FAST_GRID)
    (plot0, hints0), (plot1, hints1) = pages
    assert (plot0.title, plot0.subtitle) == ("UnB", "dez–jun")
    assert (plot1.title, plot1.subtitle) == ("UnB", "jun–dez")
    assert hints0.dayline_color == "#d55e00" and hints1.hourline_color == "#0072b2"


def test_dollar_signs_are_shown_not_parsed_as_math():
    pages = build_pages(_request(pages=(PageTexts("$x^2$", "a $ b"), PageTexts("", ""))), grid=FAST_GRID)
    plot = pages[0][0]
    assert plot.title == r"\$x^2\$"
    assert plot.subtitle == r"a \$ b"


def test_latitude_out_of_range_is_rejected():
    with pytest.raises(ValueError, match="latitude"):
        build_pages(_request(lat=80.0), grid=FAST_GRID)


def test_default_overlays_unless_an_image_is_given(tmp_path):
    (_, hints), _ = build_pages(_request(), grid=FAST_GRID)
    assert {o.name for o in hints.overlays} == {"logo", "compass"}

    (_, hints), _ = build_pages(_request(logo=_png()), grid=FAST_GRID, image_dir=tmp_path)
    logo = next(o for o in hints.overlays if o.name == "logo")
    assert logo.image_path.startswith(str(tmp_path))


# --- the files ---------------------------------------------------------------


def test_make_sundial_returns_two_pngs_and_a_two_page_pdf():
    result = make_sundial(_request(logo=_png()), grid=FAST_GRID)
    assert len(result.pngs) == 2
    assert all(png.startswith(b"\x89PNG") for png in result.pngs)
    assert result.pdf.startswith(b"%PDF")
    assert len(re.findall(rb"/Type\s*/Page\b", result.pdf)) == 2


def test_make_sundial_computes_through_the_given_map():
    calls = []

    def recording_map(fn, specs):
        specs = list(specs)
        calls.append([s.period for s in specs])
        return map(fn, specs)

    make_sundial(_request(), grid=FAST_GRID, map_fn=recording_map)
    assert calls == [[0, 1]]


# --- uploaded images ---------------------------------------------------------


@pytest.mark.parametrize("fmt", ["PNG", "JPEG"])
def test_png_and_jpeg_are_re_encoded_as_png(fmt):
    out = sanitize_image(_png(fmt=fmt))
    assert out.startswith(b"\x89PNG")
    assert Image.open(io.BytesIO(out)).size == (40, 20)


@pytest.mark.parametrize(
    "data",
    [
        b"not an image",
        b"<svg xmlns='http://www.w3.org/2000/svg'/>",
        _png(fmt="GIF"),
        _png(MAX_IMAGE_SIDE + 1, 10),
        b"\x89PNG" + b"0" * MAX_IMAGE_BYTES,
    ],
    ids=["text", "svg", "gif", "too-wide", "too-big"],
)
def test_other_uploads_are_rejected(data):
    with pytest.raises(ValueError, match="image"):
        sanitize_image(data)
