import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from accuratum.core.spec import (
    MAX_LATITUDE,
    GridConfig,
    Location,
    SundialSpec,
    TimeFrame,
    spec_from_dict,
    spec_hash,
    spec_to_dict,
)

TZ_SP = ZoneInfo("America/Sao_Paulo")


def _sample_spec() -> SundialSpec:
    return SundialSpec(
        location=Location(lat=-15.78, lon=-47.92, timezone="America/Sao_Paulo", name="Brasilia"),
        timeframe=TimeFrame(
            start=datetime(2025, 12, 21, tzinfo=TZ_SP),
            end=datetime(2026, 6, 21, tzinfo=TZ_SP),
        ),
        plumb_length=1.5,
        grid=GridConfig(dayline_day_step_days=7, time_step_minutes=20),
    )


def test_timeframe_rejects_naive_datetimes():
    naive = datetime(2026, 1, 1)
    with pytest.raises(ValueError):
        TimeFrame(start=naive, end=naive)


def test_spec_dict_roundtrip_preserves_all_fields():
    original = _sample_spec()
    data = spec_to_dict(original)
    restored = spec_from_dict(data)

    assert restored.location == original.location
    assert restored.timeframe == original.timeframe
    assert restored.plumb_length == original.plumb_length
    assert restored.grid == original.grid
    assert restored.sundial_type == original.sundial_type


def test_spec_json_roundtrip_via_dumps_loads():
    original = _sample_spec()
    blob = json.dumps(spec_to_dict(original))
    restored = spec_from_dict(json.loads(blob))
    assert restored.timeframe == original.timeframe
    assert restored.location == original.location


def test_timeframe_iso_strings_carry_timezone():
    spec = _sample_spec()
    data = spec_to_dict(spec)
    assert "-03:00" in data["timeframe"]["start"]
    assert "-03:00" in data["timeframe"]["end"]


def test_year_and_period_roundtrip():
    spec = _sample_spec()
    spec.year, spec.period = 2026, 0
    restored = spec_from_dict(spec_to_dict(spec))
    assert (restored.year, restored.period) == (2026, 0)


def test_spec_hash_ignores_location_name():
    a = _sample_spec()
    b = spec_from_dict(spec_to_dict(a))
    b.location = Location(lat=a.location.lat, lon=a.location.lon, timezone=a.location.timezone, name="Other")
    assert spec_hash(a) == spec_hash(b)


def test_spec_hash_changes_with_any_geometry_input():
    a = _sample_spec()
    b = spec_from_dict(spec_to_dict(a))
    b.plumb_length = 2.0
    c = spec_from_dict(spec_to_dict(a))
    c.grid = GridConfig(time_step_minutes=10)
    assert len({spec_hash(a), spec_hash(b), spec_hash(c)}) == 3


@pytest.mark.parametrize("lat", [MAX_LATITUDE, -MAX_LATITUDE, 0.0])
def test_location_accepts_latitudes_in_range(lat):
    assert Location(lat=lat, lon=0.0, timezone="UTC").lat == lat


@pytest.mark.parametrize("lat", [MAX_LATITUDE + 0.01, -MAX_LATITUDE - 0.01, 90.0])
def test_location_rejects_latitudes_out_of_range(lat):
    with pytest.raises(ValueError, match=f"±{MAX_LATITUDE:g}°"):
        Location(lat=lat, lon=0.0, timezone="UTC")


# --- solstice timeframe ------------------------------------------------------


@pytest.mark.parametrize(
    "period, start, end",
    [
        (0, datetime(2025, 12, 21, tzinfo=TZ_SP), datetime(2026, 6, 21, tzinfo=TZ_SP)),
        (1, datetime(2026, 6, 21, tzinfo=TZ_SP), datetime(2026, 12, 21, tzinfo=TZ_SP)),
    ],
)
def test_solstice_timeframe_spans_half_a_year(period, start, end):
    from accuratum.core.spec import solstice_timeframe

    assert solstice_timeframe(2026, period, TZ_SP) == TimeFrame(start=start, end=end)


def test_solstice_timeframe_rejects_an_unknown_period():
    from accuratum.core.spec import solstice_timeframe

    with pytest.raises(ValueError, match="period"):
        solstice_timeframe(2026, 2, TZ_SP)


# --- input validation --------------------------------------------------------
# Specs arrive from project files and, later, from web requests: reject
# anything that isn't a sane sundial, so one request can't exhaust a server.

NAN, INF = float("nan"), float("inf")


def _dict_with(path: str, value) -> dict:
    """``_sample_spec()`` as a dict, with the dotted *path* set to *value*."""
    data = spec_to_dict(_sample_spec())
    *parents, key = path.split(".")
    target = data
    for parent in parents:
        target = target[parent]
    target[key] = value
    return data


INVALID = [
    ("location.lat", NAN),
    ("location.lat", INF),
    ("location.lon", NAN),
    ("location.lon", 180.01),
    ("location.lon", -180.01),
    ("location.timezone", "Mars/Olympus_Mons"),
    ("location.timezone", "../../etc/passwd"),
    ("timeframe.end", "2025-12-20T00:00:00-03:00"),  # before the start
    ("timeframe.end", "2027-12-22T00:00:00-03:00"),  # longer than a year
    ("grid.line_points", 1),
    ("grid.line_points", 10_001),
    ("grid.line_points", 500.5),
    ("grid.line_points", True),
    ("grid.time_step_minutes", 0),
    ("grid.time_step_minutes", 241),
    ("grid.dayline_day_step_days", 0),
    ("grid.dayline_day_step_days", 184),
    ("grid.hourline_day_step_days", 0),
    ("grid.hourline_day_step_days", 184),
    ("grid.horizon_degrees", NAN),
    ("grid.horizon_degrees", -1.0),
    ("grid.horizon_degrees", 46.0),
    ("plumb_length", 0.0),
    ("plumb_length", -1.0),
    ("plumb_length", NAN),
    ("plumb_length", INF),
    ("year", 1900),
    ("year", 2101),
    ("year", 2026.0),
    ("period", 2),
]


@pytest.mark.parametrize("path, value", INVALID)
def test_spec_from_dict_rejects_invalid_inputs(path, value):
    with pytest.raises(ValueError, match=path.split(".")[-1]):
        spec_from_dict(_dict_with(path, value))


@pytest.mark.parametrize(
    "path, value",
    [
        ("location.lon", 180.0),
        ("location.lon", -180.0),
        ("grid.line_points", 2),
        ("grid.line_points", 10_000),
        ("grid.time_step_minutes", 240),
        ("grid.horizon_degrees", 0),
        ("plumb_length", 3),
        ("year", 1901),
        ("year", 2100),
        ("period", 1),
        ("period", None),
    ],
)
def test_spec_from_dict_accepts_inputs_at_the_bounds(path, value):
    spec_from_dict(_dict_with(path, value))


def test_nan_latitude_is_rejected_when_built_directly():
    with pytest.raises(ValueError, match="lat"):
        Location(lat=NAN, lon=0.0, timezone="UTC")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("location"),
        lambda d: d["grid"].update(unknown_knob=1),
        lambda d: d["timeframe"].update(start=12345),
        lambda d: d.update(location="Brasilia"),
    ],
)
def test_spec_from_dict_reports_malformed_data_as_value_error(mutate):
    data = spec_to_dict(_sample_spec())
    mutate(data)
    with pytest.raises(ValueError, match="spec"):
        spec_from_dict(data)
