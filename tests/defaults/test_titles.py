from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from accuratum.core.spec import Location, SundialSpec, TimeFrame
from accuratum.defaults.titles import default_subtitle, default_title

TZ_SP = ZoneInfo("America/Sao_Paulo")
FRAME = TimeFrame(start=datetime(2025, 12, 21, tzinfo=TZ_SP), end=datetime(2026, 6, 21, tzinfo=TZ_SP))


def _spec(lat=-15.6, lon=-47.65, name=None) -> SundialSpec:
    return SundialSpec(location=Location(lat=lat, lon=lon, timezone="America/Sao_Paulo", name=name), timeframe=FRAME)


def test_title_is_the_location_name():
    assert default_title(_spec(name="Planaltina, DF")) == "Planaltina, DF"


@pytest.mark.parametrize(
    "lat, lon, expected",
    [(-15.6, -47.65, "15.60° S, 47.65° W"), (55.95, 3.19, "55.95° N, 3.19° E"), (0.0, 0.0, "0.00° N, 0.00° E")],
)
def test_title_falls_back_to_coordinates(lat, lon, expected):
    assert default_title(_spec(lat, lon)) == expected


def test_subtitle_is_the_timeframe():
    assert default_subtitle(_spec()) == "2025-12-21 / 2026-06-21"
