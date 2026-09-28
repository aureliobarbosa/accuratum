"""Accuratum CLI — constructs a SundialSpec and renders it via the matplotlib backend.

The CLI is the only place I/O lives: argv parsing, geocoding, timezone
lookup, current time, file output. Everything below the
``SundialSpec`` construction is pure (see :func:`accuratum.core.builder.build_plot`).
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from importlib.resources import files
from typing import Sequence
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from timezonefinder import timezone_at  # noqa: E402

from accuratum.core.builder import build_plot  # noqa: E402
from accuratum.core.hints import Overlay, RenderHints  # noqa: E402
from accuratum.core.spec import GridConfig, Location, SundialSpec, TimeFrame  # noqa: E402
from accuratum.core.spec_io import load_spec, save_spec  # noqa: E402
from accuratum.location import location_to_latitude_longitude  # noqa: E402
from accuratum.renderers import matplotlib_backend, svg_backend  # noqa: E402

DEFAULT_OUTPUT = "accuratum.png"
DEFAULT_LINE_POINTS = 500
DEFAULT_TIME_STEP_MIN = 20
DEFAULT_DAYLINE_DAY_STEP = 7
DEFAULT_HOURLINE_DAY_STEP = 1
DEFAULT_LABEL_FONTSIZE = 7.0
SOLSTICE_DAY = 21

DEFAULT_LOGO_PATH = str(files("accuratum").joinpath("fig", "unb_basic.jpg"))
DEFAULT_LOGO_RECT = (0.12, 0.75, 0.12, 0.12)
DEFAULT_COMPASS_PATH = str(files("accuratum").joinpath("fig", "rosa.png"))
DEFAULT_COMPASS_RECT = (0.78, 0.75, 0.12, 0.12)


def parse_lat_long(value: str) -> tuple[float, float]:
    cleaned = value.strip().lstrip("(").rstrip(")")
    parts = [p.strip() for p in cleaned.split(",")]
    if len(parts) != 2:
        raise ValueError(f"expected 'LAT,LON', got {value!r}")
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError(f"could not parse {value!r} as two floats.")


def parse_rect(value: str) -> tuple[float, float, float, float]:
    cleaned = value.strip().lstrip("(").rstrip(")")
    parts = [p.strip() for p in cleaned.split(",")]
    if len(parts) != 4:
        raise ValueError(f"expected 'LEFT,BOTTOM,WIDTH,HEIGHT', got {value!r}")
    try:
        return tuple(float(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        raise ValueError(f"could not parse {value!r} as four floats.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="accuratum",
        description=(
            "Generate an Accuratum sundial image for a given location. "
            "Provide either a free-text location or explicit --lat-long."
        ),
    )
    parser.add_argument("location", nargs="?", default=None)
    parser.add_argument("--lat-long", type=parse_lat_long, default=None, metavar="LAT,LON")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT)
    parser.add_argument("--plumb-length", type=float, default=1.0)
    parser.add_argument(
        "--period",
        type=int,
        choices=(0, 1),
        default=0,
        help="0 = Dec(prev) -> Jun(curr), 1 = Jun(curr) -> Dec(curr).",
    )
    parser.add_argument("--timezone", default=None)
    parser.add_argument("--line-points", type=int, default=DEFAULT_LINE_POINTS)
    parser.add_argument("--time-step", type=int, default=DEFAULT_TIME_STEP_MIN, metavar="MINUTES")
    parser.add_argument("--dayline-day-step", type=int, default=DEFAULT_DAYLINE_DAY_STEP, metavar="DAYS")
    parser.add_argument("--hourline-day-step", type=int, default=DEFAULT_HOURLINE_DAY_STEP, metavar="DAYS")
    parser.add_argument("--logo", default=None, metavar="PATH")
    parser.add_argument("--logo-rect", type=parse_rect, default=None, metavar="LEFT,BOTTOM,WIDTH,HEIGHT")
    parser.add_argument("--compass", default=None, metavar="PATH")
    parser.add_argument("--compass-rect", type=parse_rect, default=None, metavar="LEFT,BOTTOM,WIDTH,HEIGHT")
    parser.add_argument("--label-fontsize", type=float, default=DEFAULT_LABEL_FONTSIZE, metavar="PT")
    parser.add_argument(
        "--spec",
        default=None,
        metavar="PATH",
        help=(
            "Load a SundialSpec from a JSON file. When given, location/timeframe/"
            "grid/plumb-length args are ignored and the spec is used as-is. "
            "Overlay (--logo/--compass) and render flags still apply."
        ),
    )
    parser.add_argument(
        "--save-spec",
        default=None,
        metavar="PATH",
        help="Also write the resolved SundialSpec to PATH as JSON before rendering.",
    )
    parser.add_argument(
        "--canvas-size-mm",
        type=_parse_canvas_mm,
        default=None,
        metavar="WIDTH,HEIGHT",
        help=(
            "SVG canvas size in millimetres, e.g. --canvas-size-mm=6000,2000 for a "
            "6m x 2m panel. Defaults to 297,210 (A4 landscape). Ignored for raster output."
        ),
    )
    return parser


def _parse_canvas_mm(value: str) -> tuple[float, float]:
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 2:
        raise ValueError(f"expected 'WIDTH,HEIGHT', got {value!r}")
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError(f"could not parse {value!r} as two floats.")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.location is not None and args.lat_long is not None:
        parser.error("provide either a location string or --lat-long, not both.")
    return args


def resolve_location(args: argparse.Namespace) -> tuple[float, float]:
    if args.lat_long is not None:
        return args.lat_long
    if args.location is None:
        raise SystemExit("error: provide a location string or --lat-long")
    latlon = location_to_latitude_longitude(args.location)
    if latlon is None:
        raise SystemExit(f"error: could not resolve location {args.location!r} via geocoder.")
    return latlon


def _solstice_timeframe(now: datetime, period: int) -> TimeFrame:
    """Build a TimeFrame from the canonical solstice pair for *now*'s year."""
    tz = now.tzinfo
    year = now.year
    dec_prev = datetime(year - 1, 12, SOLSTICE_DAY, tzinfo=tz)
    jun_curr = datetime(year, 6, SOLSTICE_DAY, tzinfo=tz)
    dec_curr = datetime(year, 12, SOLSTICE_DAY, tzinfo=tz)
    if period == 0:
        return TimeFrame(start=dec_prev, end=jun_curr)
    return TimeFrame(start=jun_curr, end=dec_curr)


def _resolve_overlay(
    cli_path: str | None,
    cli_rect: tuple[float, float, float, float] | None,
    default_path: str,
    default_rect: tuple[float, float, float, float],
    name: str,
) -> Overlay:
    path = cli_path if cli_path is not None else default_path
    rect = cli_rect if cli_rect is not None else default_rect
    if not os.path.isfile(path):
        raise SystemExit(f"error: {name} file not found: {path}")
    return Overlay(image_path=path, rect=rect)


def _spec_from_args(args: argparse.Namespace) -> SundialSpec:
    """Build a SundialSpec from CLI args (no --spec given)."""
    lat, lon = resolve_location(args)
    tz_str = args.timezone or timezone_at(lat=lat, lng=lon) or "UTC"
    tz = ZoneInfo(tz_str)
    now = datetime.now(tz=tz)
    return SundialSpec(
        location=Location(lat=lat, lon=lon, timezone=tz_str),
        timeframe=_solstice_timeframe(now, args.period),
        plumb_length=args.plumb_length,
        grid=GridConfig(
            dayline_day_step_days=args.dayline_day_step,
            line_points=args.line_points,
            hourline_day_step_days=args.hourline_day_step,
            time_step_minutes=args.time_step,
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.spec is not None:
        spec = load_spec(args.spec)
    else:
        spec = _spec_from_args(args)

    if args.save_spec is not None:
        save_spec(spec, args.save_spec)
        print(f"Saved SundialSpec to {args.save_spec}")

    overlays = [
        _resolve_overlay(args.logo, args.logo_rect, DEFAULT_LOGO_PATH, DEFAULT_LOGO_RECT, "logo"),
        _resolve_overlay(args.compass, args.compass_rect, DEFAULT_COMPASS_PATH, DEFAULT_COMPASS_RECT, "compass"),
    ]
    hints = RenderHints(
        overlays=overlays,
        label_fontsize=args.label_fontsize,
        canvas_size_mm=args.canvas_size_mm,
    )

    plot = build_plot(spec)
    _save(plot, hints, args.output)
    print(f"Saved Accuratum clock to {args.output}")
    return 0


def _save(plot, hints: RenderHints, output: str) -> None:
    """Pick renderer by *output* extension and write to disk."""
    ext = os.path.splitext(output)[1].lower()
    if ext == ".svg":
        svg = svg_backend.render(plot, hints)
        with open(output, "w", encoding="utf-8") as fh:
            fh.write(svg)
        return
    fig, _ = matplotlib_backend.render(plot, hints)
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


# Re-export timedelta to keep test_cli imports stable
__all__ = ["build_parser", "main", "parse_lat_long", "parse_rect", "resolve_location", "timedelta"]


if __name__ == "__main__":
    sys.exit(main())
