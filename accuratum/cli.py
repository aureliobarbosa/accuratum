import argparse
import sys
from datetime import datetime
from typing import Sequence
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from timezonefinder import timezone_at  # noqa: E402

from accuratum.astronomy import compute_blocks, dayline_grid, hourline_grid  # noqa: E402
from accuratum.datetime_utils import (  # noqa: E402
    frame_periods,
    get_solstices,
)
from accuratum.graph import plot_solar_clock  # noqa: E402
from accuratum.location import location_to_latitude_longitude  # noqa: E402

DEFAULT_OUTPUT = "accuratum.png"


def parse_lat_long(value: str) -> tuple[float, float]:
    """Parse a 'LAT,LON' (with optional parens/spaces) string into two floats."""
    cleaned = value.strip().lstrip("(").rstrip(")")
    parts = [p.strip() for p in cleaned.split(",")]
    if len(parts) != 2:
        raise ValueError(f"expected 'LAT,LON', got {value!r}")
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError(f"could not parse {value!r} as two floats.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="accuratum",
        description=(
            "Generate an Accuratum sundial image for a given location. "
            "Provide either a free-text location or explicit --lat-long."
        ),
    )
    parser.add_argument(
        "location",
        nargs="?",
        default=None,
        help="Free-text location (e.g. 'belem, brazil'). Resolved via geocoding. Mutually exclusive with --lat-long.",
    )
    parser.add_argument(
        "--lat-long",
        type=parse_lat_long,
        default=None,
        metavar="LAT,LON",
        help=(
            "Explicit latitude and longitude in decimal degrees. "
            "For negative values use '=' syntax, e.g. --lat-long=-15.78,-47.92."
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_OUTPUT,
        help=f"Output image path (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--plumb-length",
        type=float,
        default=1.0,
        help="Plumb (gnomon) length used to scale the shadow lines.",
    )
    parser.add_argument(
        "--period",
        type=int,
        choices=(0, 1),
        default=0,
        help="Which half-year solstice frame to render: 0 = Dec(prev)->Jun(curr), 1 = Jun(curr)->Dec(curr).",
    )
    parser.add_argument(
        "--timezone",
        default=None,
        help="IANA timezone override (e.g. 'America/Sao_Paulo'). "
        "If omitted, uses the oficial timezone at the place specified "
        "using either location or --lat-long parameters.",
    )
    return parser


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.location is not None and args.lat_long is not None:
        parser.error("provide either a location string or --lat-long, not both.")
    return args


def resolve_location(args: argparse.Namespace) -> tuple[float, float]:
    """Return (lat, lon) for the CLI args, geocoding if necessary."""
    if args.lat_long is not None:
        return args.lat_long
    if args.location is None:
        raise SystemExit("error: provide a location string or --lat-long")
    latlon = location_to_latitude_longitude(args.location)
    if latlon is None:
        raise SystemExit(f"error: could not resolve location {args.location!r} via geocoder.")
    return latlon


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    lat, lon = resolve_location(args)

    tz_str = args.timezone or timezone_at(lat=lat, lng=lon) or "UTC"
    tz = ZoneInfo(tz_str)
    now = datetime.now(tz=tz)

    periods = frame_periods(get_solstices(now))
    period = periods[args.period]
    daylines = dayline_grid(period, lat=lat, lon=lon)
    hourlines = hourline_grid(period, lat=lat, lon=lon)

    blocks_x, blocks_y = compute_blocks(
        daylines_grid=daylines,
        hourlines_grid=hourlines,
        lat=lat,
        lon=lon,
        plumb_length=args.plumb_length,
    )

    fig, _ = plot_solar_clock(blocks_x, blocks_y, plumb_xy=(0, 0))
    fig.savefig(args.output, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved Accuratum clock to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
