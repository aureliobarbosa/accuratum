import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from accuratum.core.spec import (
    GridConfig,
    Location,
    SundialSpec,
    TimeFrame,
    spec_from_dict,
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
    assert restored.spec_version == original.spec_version


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
