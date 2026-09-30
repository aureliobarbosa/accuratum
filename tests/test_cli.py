import json
from unittest.mock import patch

import pytest

from accuratum.cli import build_parser, parse_lat_long, parse_rect, resolve_location
from accuratum.core.project_io import DATASET_FILE, PROJECT_FILE, load_project

# Coarse grid args for end-to-end CLI tests — keep the astropy/astroplan work small.
# Larger day steps reduce how many days astroplan's sun_rise_time is evaluated on.
FAST_GRID_ARGS = [
    "--line-points",
    "20",
    "--time-step",
    "120",
    "--dayline-day-step",
    "30",
    "--hourline-day-step",
    "30",
]


@pytest.fixture(autouse=True)
def _in_tmp_dir(tmp_path, monkeypatch):
    """Generating runs write a project folder into the current directory."""
    monkeypatch.chdir(tmp_path)


# --- parse_lat_long -----------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("10.5,-20.25", (10.5, -20.25)),
        ("(10.5,-20.25)", (10.5, -20.25)),
        (" 10.5 , -20.25 ", (10.5, -20.25)),
        ("(-15.78, -47.92)", (-15.78, -47.92)),
    ],
)
def test_parse_lat_long_accepts_formats(value, expected):
    lat, lon = parse_lat_long(value)
    assert lat == pytest.approx(expected[0])
    assert lon == pytest.approx(expected[1])


@pytest.mark.parametrize("value", ["not-a-pair", "10.5", "a,b", "1,2,3"])
def test_parse_lat_long_rejects_invalid(value):
    with pytest.raises(ValueError):
        parse_lat_long(value)


# --- argument parser ----------------------------------------------------------


def test_parser_accepts_location_positional():
    parser = build_parser()
    args = parser.parse_args(["belem, brazil"])
    assert args.location == "belem, brazil"
    assert args.lat_long is None


def test_parser_accepts_lat_long():
    parser = build_parser()
    args = parser.parse_args(["--lat-long=-15.78,-47.92"])
    assert args.location is None
    assert args.lat_long == (-15.78, -47.92)


def test_parser_accepts_positive_lat_long_without_equals():
    parser = build_parser()
    args = parser.parse_args(["--lat-long", "15.78,47.92"])
    assert args.lat_long == (15.78, 47.92)


def test_parser_rejects_both_location_sources():
    with pytest.raises(SystemExit):
        # Parsing alone is not enough — we enforce mutual exclusion via parser.error
        # in _parse_args; call the top-level entry point that triggers it.
        from accuratum.cli import _parse_args

        _parse_args(["belem", "--lat-long=1,2"])


def test_parser_default_output_is_none_so_it_goes_in_the_project_folder():
    parser = build_parser()
    args = parser.parse_args(["--lat-long=0,0"])
    assert args.output is None


def test_parser_custom_output():
    parser = build_parser()
    args = parser.parse_args(["--lat-long=0,0", "--output", "out.pdf"])
    assert args.output == "out.pdf"


def test_parser_plumb_length_and_period_defaults():
    parser = build_parser()
    args = parser.parse_args(["--lat-long=0,0"])
    assert args.plumb_length == 1.0
    assert args.period == 0


def test_parser_grid_resolution_defaults_and_overrides():
    from accuratum.cli import (
        DEFAULT_DAYLINE_DAY_STEP,
        DEFAULT_HOURLINE_DAY_STEP,
        DEFAULT_LINE_POINTS,
        DEFAULT_TIME_STEP_MIN,
    )

    parser = build_parser()
    args = parser.parse_args(["--lat-long=0,0"])
    assert args.line_points == DEFAULT_LINE_POINTS
    assert args.time_step == DEFAULT_TIME_STEP_MIN
    assert args.dayline_day_step == DEFAULT_DAYLINE_DAY_STEP
    assert args.hourline_day_step == DEFAULT_HOURLINE_DAY_STEP

    args = parser.parse_args(
        [
            "--lat-long=0,0",
            "--line-points",
            "20",
            "--time-step",
            "120",
            "--dayline-day-step",
            "30",
            "--hourline-day-step",
            "30",
        ]
    )
    assert args.line_points == 20
    assert args.time_step == 120
    assert args.dayline_day_step == 30
    assert args.hourline_day_step == 30


# --- resolve_location --------------------------------------------------------


def test_resolve_location_from_lat_long():
    parser = build_parser()
    args = parser.parse_args(["--lat-long=12.5,-34.25"])
    lat, lon = resolve_location(args)
    assert lat == pytest.approx(12.5)
    assert lon == pytest.approx(-34.25)


def test_resolve_location_from_string_uses_geocoder():
    parser = build_parser()
    args = parser.parse_args(["somewhere"])
    with patch(
        "accuratum.cli.location_to_latitude_longitude",
        return_value=(1.1, 2.2),
    ) as mocked:
        lat, lon = resolve_location(args)
    mocked.assert_called_once()
    assert (lat, lon) == (1.1, 2.2)


def test_resolve_location_raises_when_geocoder_returns_none():
    parser = build_parser()
    args = parser.parse_args(["nowhere"])
    with patch("accuratum.cli.location_to_latitude_longitude", return_value=None):
        with pytest.raises(SystemExit):
            resolve_location(args)


def test_resolve_location_requires_any_input():
    parser = build_parser()
    args = parser.parse_args([])
    with pytest.raises(SystemExit):
        resolve_location(args)


# --- timezone resolution -----------------------------------------------------


def test_main_uses_timezonefinder_when_timezone_omitted(tmp_path):
    from accuratum.cli import main

    out = tmp_path / "clock.png"
    with patch("accuratum.cli.timezone_at", return_value="America/Sao_Paulo") as tzf:
        exit_code = main(["--lat-long=-15.6,-47.65", "--output", str(out), *FAST_GRID_ARGS])
    assert exit_code == 0
    tzf.assert_called_once_with(lat=-15.6, lng=-47.65)


def test_main_respects_explicit_timezone_over_timezonefinder(tmp_path):
    from accuratum.cli import main

    out = tmp_path / "clock.png"
    with patch("accuratum.cli.timezone_at") as tzf:
        exit_code = main(
            [
                "--lat-long=-15.6,-47.65",
                "--timezone",
                "UTC",
                "--output",
                str(out),
                *FAST_GRID_ARGS,
            ]
        )
    assert exit_code == 0
    tzf.assert_not_called()


def test_main_falls_back_to_utc_when_timezonefinder_returns_none(tmp_path):
    from accuratum.cli import main

    out = tmp_path / "clock.png"
    with patch("accuratum.cli.timezone_at", return_value=None):
        exit_code = main(["--lat-long=0,0", "--output", str(out), *FAST_GRID_ARGS])
    assert exit_code == 0


# --- logo --------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("0.1,0.75,0.12,0.12", (0.1, 0.75, 0.12, 0.12)),
        (" 0.1 , 0.75 , 0.12 , 0.12 ", (0.1, 0.75, 0.12, 0.12)),
        ("(0.1,0.75,0.12,0.12)", (0.1, 0.75, 0.12, 0.12)),
    ],
)
def test_parse_rect_accepts_formats(value, expected):
    assert parse_rect(value) == pytest.approx(expected)


@pytest.mark.parametrize("value", ["0.1,0.75,0.12", "a,b,c,d", "1,2,3,4,5"])
def test_parse_rect_rejects_invalid(value):
    with pytest.raises(ValueError):
        parse_rect(value)


def test_parser_logo_defaults_are_none():
    parser = build_parser()
    args = parser.parse_args(["--lat-long=0,0"])
    assert args.logo is None
    assert args.logo_rect is None


def test_parser_accepts_logo_and_rect(tmp_path):
    parser = build_parser()
    args = parser.parse_args(
        [
            "--lat-long=0,0",
            "--logo",
            "some/logo.png",
            "--logo-rect",
            "0.2,0.8,0.1,0.1",
        ]
    )
    assert args.logo == "some/logo.png"
    assert args.logo_rect == (0.2, 0.8, 0.1, 0.1)


def test_main_fails_when_logo_file_missing(tmp_path):
    from accuratum.cli import main

    missing = tmp_path / "nope.png"
    out = tmp_path / "clock.png"
    with pytest.raises(SystemExit):
        main(
            [
                "--lat-long=0,0",
                "--logo",
                str(missing),
                "--output",
                str(out),
                *FAST_GRID_ARGS,
            ]
        )


# --- end-to-end --------------------------------------------------------------


def test_main_saves_output_image(tmp_path):
    from accuratum.cli import main

    out = tmp_path / "clock.png"
    exit_code = main(["--lat-long=-15.6,-47.65", "--output", str(out), *FAST_GRID_ARGS])

    assert exit_code == 0
    assert out.exists()
    assert out.stat().st_size > 0


# --- vector output formats ---------------------------------------------------


def test_main_saves_svg_through_matplotlib(tmp_path):
    from accuratum.cli import main

    out = tmp_path / "clock.svg"
    exit_code = main(["--lat-long=-15.6,-47.65", "--output", str(out), *FAST_GRID_ARGS])
    assert exit_code == 0
    # Same drawing as the PNG: .svg goes through matplotlib's own writer.
    assert "matplotlib.org" in out.read_text()


def test_canvas_size_flag_is_gone(tmp_path):
    from accuratum.cli import main

    with pytest.raises(SystemExit):
        main(["--lat-long=-15.6,-47.65", "--canvas-size-mm=6000,2000", *FAST_GRID_ARGS])


def test_main_saves_pdf_output(tmp_path):
    from accuratum.cli import main

    out = tmp_path / "clock.pdf"
    exit_code = main(["--lat-long=-15.6,-47.65", "--output", str(out), *FAST_GRID_ARGS])
    assert exit_code == 0
    assert out.exists()
    # PDF magic number — confirms matplotlib's PDF backend ran, not the PNG one.
    assert out.read_bytes().startswith(b"%PDF")


# --- project folders ---------------------------------------------------------

LATLONG = "--lat-long=-15.6,-47.65"
AUTO_DIR = "lat-15.60_lon-47.65_2026_p0"


def _generate(*extra):
    from accuratum.cli import main

    with patch("accuratum.cli.timezone_at", return_value="America/Sao_Paulo"):
        return main([LATLONG, "--year", "2026", *FAST_GRID_ARGS, *extra])


def test_generate_creates_auto_named_project_folder(tmp_path):
    assert _generate() == 0
    folder = tmp_path / AUTO_DIR
    assert (folder / PROJECT_FILE).is_file()
    assert (folder / DATASET_FILE).is_file()
    assert (folder / "accuratum.png").is_file()


def test_generate_records_year_and_period(tmp_path):
    _generate("--period", "1")
    spec = load_project(tmp_path / "lat-15.60_lon-47.65_2026_p1").spec
    assert (spec.year, spec.period) == (2026, 1)
    assert (spec.timeframe.start.year, spec.timeframe.start.month) == (2026, 6)
    assert (spec.timeframe.end.year, spec.timeframe.end.month) == (2026, 12)


def test_auto_folder_and_name_from_location_string(tmp_path):
    from accuratum.cli import main

    with (
        patch("accuratum.cli.location_to_latitude_longitude", return_value=(-15.6, -47.65)),
        patch("accuratum.cli.timezone_at", return_value="America/Sao_Paulo"),
    ):
        main(["Planaltina, DF", "--year", "2026", *FAST_GRID_ARGS])
    spec = load_project(tmp_path / "planaltina-df_2026_p0").spec
    assert spec.location.name == "Planaltina, DF"


def test_project_dir_flag_sets_the_folder(tmp_path):
    _generate("--project-dir", "mine")
    assert (tmp_path / "mine" / PROJECT_FILE).is_file()


def test_existing_project_is_not_overwritten_without_force(tmp_path):
    _generate()
    with pytest.raises(SystemExit):
        _generate()
    assert _generate("--force") == 0


def test_project_renders_without_recomputing(tmp_path):
    from accuratum.cli import main

    _generate()
    with patch("accuratum.cli.build_plot", side_effect=AssertionError("recomputed")):
        assert main(["--project", AUTO_DIR, "-o", "b.png"]) == 0
    assert (tmp_path / "b.png").is_file()


def test_project_render_defaults_into_its_folder(tmp_path):
    from accuratum.cli import main

    _generate()
    (tmp_path / AUTO_DIR / "accuratum.png").unlink()
    main(["--project", AUTO_DIR])
    assert (tmp_path / AUTO_DIR / "accuratum.png").is_file()


def test_render_settings_are_saved_and_cli_flags_win(tmp_path):
    _generate("--label-fontsize=9")
    render = json.loads((tmp_path / AUTO_DIR / PROJECT_FILE).read_text())["render"]
    assert render["label_fontsize"] == 9.0


def test_line_colors_are_saved_as_hex(tmp_path):
    _generate("--dayline-color=orange", "--hourline-color=#123ABC")
    render = json.loads((tmp_path / AUTO_DIR / PROJECT_FILE).read_text())["render"]
    assert (render["dayline_color"], render["hourline_color"]) == ("#ffa500", "#123abc")


def test_line_color_flag_overrides_a_saved_project(tmp_path):
    from accuratum.cli import main

    _generate()
    with patch("accuratum.cli._save") as save:
        main(["--project", AUTO_DIR, "--hourline-color", "black"])
    hints = save.call_args.args[1]
    assert (hints.dayline_color, hints.hourline_color) == ("#d55e00", "#000000")


def test_unknown_color_is_rejected():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--dayline-color", "not-a-color"])


def test_default_overlays_are_stored_as_package_paths(tmp_path):
    _generate()
    render = json.loads((tmp_path / AUTO_DIR / PROJECT_FILE).read_text())["render"]
    paths = {o["name"]: o["image_path"] for o in render["overlays"]}
    assert paths == {"logo": "accuratum:fig/unb_basic.jpg", "compass": "accuratum:fig/rosa.png"}


def test_hand_edited_label_is_rendered(tmp_path):
    from accuratum.cli import main

    _generate()
    path = tmp_path / AUTO_DIR / PROJECT_FILE
    data = json.loads(path.read_text())
    data["labels"].append({"text": "HELLO", "x": 0.0, "y": 1.0})
    path.write_text(json.dumps(data))
    main(["--project", AUTO_DIR, "-o", "b.svg"])
    assert "HELLO" in (tmp_path / "b.svg").read_text()


def _edit_spec(folder, **changes):
    path = folder / PROJECT_FILE
    data = json.loads(path.read_text())
    data["spec"].update(changes)
    path.write_text(json.dumps(data))


def test_edited_spec_is_an_error_until_regenerated(tmp_path):
    from accuratum.cli import main

    _generate()
    _edit_spec(tmp_path / AUTO_DIR, plumb_length=2.0)
    with pytest.raises(SystemExit, match="--regenerate"):
        main(["--project", AUTO_DIR])
    assert main(["--project", AUTO_DIR, "--regenerate"]) == 0
    assert (tmp_path / AUTO_DIR / (PROJECT_FILE + ".bak")).is_file()
    assert load_project(tmp_path / AUTO_DIR).spec.plumb_length == 2.0


def test_regenerate_recomputes_timeframe_from_year_and_period(tmp_path):
    from accuratum.cli import main

    _generate()
    _edit_spec(tmp_path / AUTO_DIR, period=1)
    main(["--project", AUTO_DIR, "--regenerate"])
    assert load_project(tmp_path / AUTO_DIR).spec.timeframe.start.month == 6


def test_project_rejects_location_arguments():
    from accuratum.cli import main

    with pytest.raises(SystemExit):
        main(["--project", "x", LATLONG])


# --- latitude range ----------------------------------------------------------


def test_latitude_out_of_range_is_a_clear_error(tmp_path):
    from accuratum.cli import main

    with patch("accuratum.cli.timezone_at") as tzf, pytest.raises(SystemExit, match="latitude 80.*±"):
        main(["--lat-long=80,15", *FAST_GRID_ARGS])
    tzf.assert_not_called()
    assert not list(tmp_path.iterdir())


def test_default_overlays_sit_in_the_header_above_the_drawing():
    from accuratum.cli import DEFAULT_OVERLAYS
    from accuratum.core.hints import RenderHints

    left, bottom, width, height = RenderHints().axes_rect
    for overlay in DEFAULT_OVERLAYS.values():
        assert overlay.rect[1] >= bottom + height
        assert overlay.rect[1] + overlay.rect[3] <= 1.0


# --- title and subtitle ------------------------------------------------------


def test_default_titles_are_saved_and_rendered(tmp_path):
    _generate("-o", "a.svg")
    data = json.loads((tmp_path / AUTO_DIR / PROJECT_FILE).read_text())
    assert (data["title"], data["subtitle"]) == ("15.60° S, 47.65° W", "2025-12-21 / 2026-06-21")
    svg = (tmp_path / "a.svg").read_text()
    assert "15.60° S, 47.65° W" in svg
    assert "2025-12-21 / 2026-06-21" in svg


def test_given_titles_are_saved_and_rendered_again(tmp_path):
    from accuratum.cli import main

    _generate("--title", "FUP Planaltina", "--subtitle", "Primeiro semestre")
    data = json.loads((tmp_path / AUTO_DIR / PROJECT_FILE).read_text())
    assert (data["title"], data["subtitle"]) == ("FUP Planaltina", "Primeiro semestre")
    main(["--project", AUTO_DIR, "-o", "b.svg"])
    svg = (tmp_path / "b.svg").read_text()
    assert "FUP Planaltina" in svg and "Primeiro semestre" in svg


def test_title_flag_with_project_is_for_this_run_only(tmp_path):
    from accuratum.cli import main

    _generate()
    main(["--project", AUTO_DIR, "--title", "Just once", "-o", "b.svg"])
    assert "Just once" in (tmp_path / "b.svg").read_text()
    assert load_project(tmp_path / AUTO_DIR).plot.title == "15.60° S, 47.65° W"


def test_regenerate_keeps_edited_texts_and_updates_default_ones(tmp_path):
    from accuratum.cli import main

    _generate("--title", "Mine")
    _edit_spec(tmp_path / AUTO_DIR, period=1)
    main(["--project", AUTO_DIR, "--regenerate"])
    plot = load_project(tmp_path / AUTO_DIR).plot
    assert (plot.title, plot.subtitle) == ("Mine", "2026-06-21 / 2026-12-21")
