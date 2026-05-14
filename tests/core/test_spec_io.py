from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from accuratum.core.spec import (
    GridConfig,
    LabelOverride,
    Location,
    SundialSpec,
    TimeFrame,
)
from accuratum.core.spec_io import load_spec, save_spec

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
        overrides=[
            LabelOverride(selector={"kind": "hourline", "hour": 6}, dx=0.1, dy=-0.2),
        ],
    )


def test_save_and_load_roundtrip(tmp_path):
    original = _sample_spec()
    path = tmp_path / "clock.json"
    save_spec(original, path)
    restored = load_spec(path)
    assert restored.location == original.location
    assert restored.timeframe == original.timeframe
    assert restored.grid == original.grid
    assert restored.overrides == original.overrides


def test_saved_file_is_pretty_printed(tmp_path):
    path = tmp_path / "clock.json"
    save_spec(_sample_spec(), path)
    text = path.read_text()
    # Indented and ends with a newline.
    assert "\n  " in text
    assert text.endswith("\n")
    # Sorted keys at top level (location < overrides < ...).
    assert text.index('"location"') < text.index('"overrides"')


def test_load_rejects_future_spec_version(tmp_path):
    path = tmp_path / "clock.json"
    save_spec(_sample_spec(), path)
    raw = path.read_text().replace('"spec_version": 1', '"spec_version": 999')
    path.write_text(raw)
    with pytest.raises(ValueError, match="version"):
        load_spec(path)


def test_override_edit_survives_roundtrip(tmp_path):
    """The whole point of spec I/O: hand-edit overrides, reload, render."""
    path = tmp_path / "clock.json"
    save_spec(_sample_spec(), path)

    # Hand-edit: change dx for hourline 6 from 0.1 to 0.5
    raw = path.read_text().replace('"dx": 0.1', '"dx": 0.5')
    path.write_text(raw)

    restored = load_spec(path)
    hour_ov = next(o for o in restored.overrides if o.selector.get("hour") == 6)
    assert hour_ov.dx == 0.5
