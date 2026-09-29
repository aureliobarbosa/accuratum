import json
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from accuratum.core.hints import Overlay, RenderHints
from accuratum.core.plot import Label, Plot, Polyline
from accuratum.core.project import Project
from accuratum.core.project_io import DATASET_FILE, PROJECT_FILE, StaleProjectError, load_project, save_project
from accuratum.core.spec import GridConfig, Location, SundialSpec, TimeFrame

TZ_SP = ZoneInfo("America/Sao_Paulo")
PLANALTINA = Location(lat=-15.6006489, lon=-47.6580608, timezone="America/Sao_Paulo", name="Planaltina")
FRAME = TimeFrame(start=datetime(2025, 12, 21, tzinfo=TZ_SP), end=datetime(2026, 6, 21, tzinfo=TZ_SP))
DAY = {"kind": "dayline", "date": "2026-01-15"}
HOUR = {"kind": "hourline", "hour": 7}
FAST_GRID = GridConfig(
    dayline_day_step_days=30, line_points=20, hourline_day_step_days=30, time_step_minutes=120, horizon_degrees=10.0
)


def _project() -> Project:
    spec = SundialSpec(location=PLANALTINA, timeframe=FRAME, grid=FAST_GRID, year=2026, period=0)
    plot = Plot(
        polylines=[
            Polyline("dayline", np.array([-5.0, 0.1, 5.0]), np.array([0.5, 0.0, 2.0]), DAY),
            Polyline("hourline", np.array([-3.0, 3.0]), np.array([2.0, -2.0]), {**HOUR, "minute_offset": -4}),
            Polyline("dayline", np.empty(0), np.empty(0), {}),
        ],
        labels=[
            Label("01/15", -5.0, 0.5, "right", "center", "dayline", {**DAY, "end": "start"}),
            Label("07h", 3.0, -2.0, "center", "bottom", "hourline", {**HOUR, "end": "end"}, hidden=True),
        ],
        data_extent=10.0,
        title="FUP",
        subtitle="",
    )
    render = RenderHints(
        overlays=[Overlay("logo.png", (0.1, 0.8, 0.1, 0.1))],
        label_fontsize=9.0,
        axes_rect=(0.1, 0.1, 0.8, 0.6),
        title_xy=(0.4, 0.9),
        subtitle_xy=(0.4, 0.85),
    )
    return Project(spec=spec, plot=plot, render=render, provenance={"accuratum": "0.2.0"})


def test_save_writes_json_and_npz(tmp_path):
    save_project(_project(), tmp_path / "p")
    assert (tmp_path / "p" / PROJECT_FILE).is_file()
    assert (tmp_path / "p" / DATASET_FILE).is_file()


def test_roundtrip_restores_everything(tmp_path):
    original = _project()
    save_project(original, tmp_path)
    restored = load_project(tmp_path)

    assert restored.spec == original.spec
    assert restored.render == original.render
    assert restored.provenance == original.provenance
    assert restored.plot.labels == original.plot.labels
    assert (restored.plot.title, restored.plot.subtitle) == ("FUP", "")
    assert len(restored.plot.polylines) == len(original.plot.polylines)
    for a, b in zip(restored.plot.polylines, original.plot.polylines):
        assert a.kind == b.kind
        assert a.metadata == b.metadata
        np.testing.assert_array_equal(a.xs, b.xs)
        np.testing.assert_array_equal(a.ys, b.ys)


def test_data_extent_is_recomputed_on_load(tmp_path):
    save_project(_project(), tmp_path)
    assert load_project(tmp_path).plot.data_extent == 10.0  # x from -5 to 5


def test_project_json_is_short_with_one_label_per_line(tmp_path):
    save_project(_project(), tmp_path)
    text = (tmp_path / PROJECT_FILE).read_text()
    assert len(text.splitlines()) < 60
    label_lines = [line for line in text.splitlines() if '"text":' in line]
    assert len(label_lines) == 2
    json.loads(text)  # still valid JSON


def test_hand_added_minimal_label_gets_defaults(tmp_path):
    save_project(_project(), tmp_path)
    path = tmp_path / PROJECT_FILE
    data = json.loads(path.read_text())
    data["labels"].append({"text": "Planaltina", "x": 0.0, "y": 3.0})
    path.write_text(json.dumps(data))
    added = load_project(tmp_path).plot.labels[-1]
    assert added == Label("Planaltina", 0.0, 3.0, "center", "center", "custom", {}, hidden=False)


def test_edited_spec_is_rejected(tmp_path):
    save_project(_project(), tmp_path)
    path = tmp_path / PROJECT_FILE
    data = json.loads(path.read_text())
    data["spec"]["plumb_length"] = 2.0
    path.write_text(json.dumps(data))
    with pytest.raises(StaleProjectError):
        load_project(tmp_path)


def test_edited_location_name_is_accepted(tmp_path):
    save_project(_project(), tmp_path)
    path = tmp_path / PROJECT_FILE
    data = json.loads(path.read_text())
    data["spec"]["location"]["name"] = "Planaltina, DF"
    path.write_text(json.dumps(data))
    assert load_project(tmp_path).spec.location.name == "Planaltina, DF"


def test_dataset_from_another_spec_is_rejected(tmp_path):
    save_project(_project(), tmp_path / "a")
    other = _project()
    other.spec.plumb_length = 2.0
    save_project(other, tmp_path / "b")
    (tmp_path / "b" / DATASET_FILE).replace(tmp_path / "a" / DATASET_FILE)
    with pytest.raises(StaleProjectError):
        load_project(tmp_path / "a")


def test_future_version_is_rejected(tmp_path):
    save_project(_project(), tmp_path)
    path = tmp_path / PROJECT_FILE
    data = json.loads(path.read_text())
    data["version"] = 999
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="version"):
        load_project(tmp_path)


def test_missing_dataset_is_rebuilt_and_labels_kept(tmp_path):
    original = _project()
    save_project(original, tmp_path)
    (tmp_path / DATASET_FILE).unlink()

    restored = load_project(tmp_path)

    assert (tmp_path / DATASET_FILE).is_file()
    assert restored.plot.labels == original.plot.labels
    assert {p.kind for p in restored.plot.polylines} == {"dayline", "hourline"}


def test_legacy_render_keys_are_ignored():
    from accuratum.core.project import hints_from_dict

    hints = hints_from_dict({"canvas_size_mm": [6000, 2000], "units": "mm", "label_fontsize": 9.0})
    assert hints.label_fontsize == 9.0
    assert not hasattr(hints, "canvas_size_mm")


def test_project_json_shows_the_texts_drawn(tmp_path):
    save_project(_project(), tmp_path)
    data = json.loads((tmp_path / PROJECT_FILE).read_text())
    assert (data["title"], data["subtitle"]) == ("FUP", "")


def test_project_without_texts_gets_the_defaults(tmp_path):
    save_project(_project(), tmp_path)
    path = tmp_path / PROJECT_FILE
    data = json.loads(path.read_text())
    del data["title"], data["subtitle"]
    path.write_text(json.dumps(data))
    plot = load_project(tmp_path).plot
    assert (plot.title, plot.subtitle) == ("Planaltina", "2025-12-21 / 2026-06-21")
