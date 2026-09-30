import json
from datetime import date
from pathlib import Path

import pytest

from accuratum.core.spec import MAX_LATITUDE, GridConfig
from accuratum_web.gallery import GALLERY_DIR, UNIVERSITIES, generate, half_year

FAST_GRID = GridConfig(dayline_day_step_days=30, line_points=20, hourline_day_step_days=10, time_step_minutes=60)


@pytest.mark.parametrize(
    "today, expected",
    [
        (date(2026, 1, 5), (2026, 0)),
        (date(2026, 6, 20), (2026, 0)),
        (date(2026, 6, 21), (2026, 1)),
        (date(2026, 9, 30), (2026, 1)),
        (date(2026, 12, 20), (2026, 1)),
        (date(2026, 12, 21), (2027, 0)),
    ],
)
def test_half_year_in_progress(today, expected):
    assert half_year(today) == expected


def test_universities_are_within_the_supported_latitudes():
    assert len(UNIVERSITIES) == 10
    for uni in UNIVERSITIES:
        assert abs(uni.lat) <= MAX_LATITUDE
        assert -180 <= uni.lon <= 180


def test_generate_writes_one_image_per_city_and_an_index(tmp_path):
    entries = generate(tmp_path, date(2026, 9, 30), grid=FAST_GRID, universities=UNIVERSITIES[:2])
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index == entries
    assert [e["city"] for e in index] == [u.city for u in UNIVERSITIES[:2]]
    for entry in index:
        assert (tmp_path / entry["image"]).read_bytes().startswith(b"\x89PNG")
        assert entry["subtitle"] == "2026-06-21 / 2026-12-21"


def test_images_are_titled_with_the_city():
    from accuratum_web.gallery import title_for

    assert [title_for(u) for u in UNIVERSITIES[:2]] == ["Brasília", "Santiago"]


def test_the_accuratum_logo_except_at_unb():
    from accuratum.defaults.overlays import ACCURATUM_LOGO, DEFAULT_OVERLAYS
    from accuratum_web.gallery import logo_for

    logos = {u.city: logo_for(u) for u in UNIVERSITIES}
    assert logos.pop("Brasília") == DEFAULT_OVERLAYS["logo"].image_path
    assert set(logos.values()) == {ACCURATUM_LOGO}


def test_the_published_gallery_is_complete():
    index_file = Path(GALLERY_DIR) / "index.json"
    if not index_file.exists():
        pytest.skip("gallery not generated yet")
    index = json.loads(index_file.read_text(encoding="utf-8"))
    assert [e["city"] for e in index] == [u.city for u in UNIVERSITIES]
    for entry in index:
        assert (Path(GALLERY_DIR) / entry["image"]).is_file()


@pytest.mark.parametrize("city, file", [("Brasília", "brasilia"), ("Ciudad de México", "ciudad-de-mexico")])
def test_image_names_keep_accented_letters(city, file):
    from accuratum_web.gallery import _slug

    assert _slug(city) == file
