from unittest.mock import patch

import pytest

from accuratum.cli import build_parser, parse_lat_long, resolve_location

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


def test_parser_default_output_is_png():
    parser = build_parser()
    args = parser.parse_args(["--lat-long=0,0"])
    assert args.output.endswith(".png")


def test_parser_custom_output():
    parser = build_parser()
    args = parser.parse_args(["--lat-long=0,0", "--output", "out.pdf"])
    assert args.output == "out.pdf"


def test_parser_plumb_length_and_period_defaults():
    parser = build_parser()
    args = parser.parse_args(["--lat-long=0,0"])
    assert args.plumb_length == 1.0
    assert args.period == 0


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
        exit_code = main(["--lat-long=-15.6,-47.65", "--output", str(out)])
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
            ]
        )
    assert exit_code == 0
    tzf.assert_not_called()


def test_main_falls_back_to_utc_when_timezonefinder_returns_none(tmp_path):
    from accuratum.cli import main

    out = tmp_path / "clock.png"
    with patch("accuratum.cli.timezone_at", return_value=None):
        exit_code = main(["--lat-long=0,0", "--output", str(out)])
    assert exit_code == 0


# --- end-to-end --------------------------------------------------------------


def test_main_saves_output_image(tmp_path):
    from accuratum.cli import main

    out = tmp_path / "clock.png"
    exit_code = main(["--lat-long=-15.6,-47.65", "--output", str(out)])

    assert exit_code == 0
    assert out.exists()
    assert out.stat().st_size > 0
