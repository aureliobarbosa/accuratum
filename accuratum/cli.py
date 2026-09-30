"""Accuratum CLI — generates a project folder, or renders a saved one.

The CLI is the only place I/O lives: argv parsing, geocoding, timezone
lookup, current time, file output. Everything below the
``SundialSpec`` construction is pure (see :func:`accuratum.core.builder.build_plot`).

Two modes:

- **generate** (a location or ``--lat-long``): compute the sundial and save it
  as a project folder (``project.json`` + ``polylines.npz``), then render it;
- **render** (``--project DIR``): load a saved project, including hand-edited
  labels, and render it without recomputing. ``--regenerate`` recomputes it
  from its (edited) spec instead.
"""

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import replace
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Sequence
from zoneinfo import ZoneInfo

from matplotlib.colors import to_hex
from timezonefinder import timezone_at

from accuratum.core.builder import build_plot
from accuratum.core.hints import RenderHints
from accuratum.core.plot import Plot
from accuratum.core.project import Project, hints_from_dict
from accuratum.core.project_io import PROJECT_FILE, StaleProjectError, load_project, save_project
from accuratum.core.spec import (
    MAX_LATITUDE,
    GridConfig,
    Location,
    SundialSpec,
    solstice_timeframe,
    spec_from_dict,
)
from accuratum.defaults.overlays import DEFAULT_OVERLAYS, default_render_hints, resolve_image_path
from accuratum.defaults.titles import default_subtitle, default_title
from accuratum.location import location_to_latitude_longitude
from accuratum.renderers import matplotlib_backend

DEFAULT_OUTPUT_NAME = "accuratum.png"
DEFAULT_LINE_POINTS = 500
DEFAULT_TIME_STEP_MIN = 20
DEFAULT_DAYLINE_DAY_STEP = 7
DEFAULT_HOURLINE_DAY_STEP = 1


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


def parse_color(value: str) -> str:
    """Any matplotlib color (``orange``, ``#123ABC``, ``C0``), saved as ``#rrggbb``."""
    try:
        return to_hex(value)
    except ValueError:
        raise ValueError(f"not a color: {value!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="accuratum",
        description=(
            "Generate an Accuratum sundial for a location and save it as a project folder "
            "(project.json + polylines.npz), or render a saved project with --project."
        ),
    )
    parser.add_argument("location", nargs="?", default=None)
    parser.add_argument(
        "--lat-long",
        type=parse_lat_long,
        default=None,
        metavar="LAT,LON",
        help=f"Latitude within ±{MAX_LATITUDE:g}°. Negative values need '=': --lat-long=-15.78,-47.92.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help=f"Image to write (.png, .pdf, .svg). Defaults to {DEFAULT_OUTPUT_NAME} in the project folder.",
    )
    parser.add_argument("--plumb-length", type=float, default=1.0)
    parser.add_argument("--year", type=int, default=None, help="Defaults to the current year.")
    parser.add_argument(
        "--period",
        type=int,
        choices=(0, 1),
        default=0,
        help="0 = Dec(year-1) -> Jun(year), 1 = Jun(year) -> Dec(year).",
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
    parser.add_argument("--label-fontsize", type=float, default=None, metavar="PT")
    parser.add_argument(
        "--dayline-color",
        type=parse_color,
        default=None,
        metavar="COLOR",
        help=f"Name or #rrggbb. Default {RenderHints.dayline_color}.",
    )
    parser.add_argument(
        "--hourline-color",
        type=parse_color,
        default=None,
        metavar="COLOR",
        help=f"Name or #rrggbb. Default {RenderHints.hourline_color}.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Defaults to the location name, or its coordinates. '' for none. With --project: this run only.",
    )
    parser.add_argument(
        "--subtitle", default=None, help="Defaults to the timeframe. '' for none. With --project: this run only."
    )
    parser.add_argument(
        "--project-dir",
        default=None,
        metavar="DIR",
        help="Folder for a new project. Defaults to <location>_<year>_p<period> in the current directory.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing project folder.")
    parser.add_argument(
        "--project",
        default=None,
        metavar="DIR",
        help=(
            "Render a saved project folder without recomputing it. Render flags "
            "(--logo, --label-fontsize, ...) override its saved render settings for this run."
        ),
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help=(
            "With --project: recompute geometry and labels from the project's spec "
            "(after editing it). The old project.json is kept as project.json.bak."
        ),
    )
    return parser


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.location is not None and args.lat_long is not None:
        parser.error("provide either a location string or --lat-long, not both.")
    if args.project is not None and (args.location is not None or args.lat_long is not None):
        parser.error("--project renders a saved project; don't give a location with it.")
    if args.regenerate and args.project is None:
        parser.error("--regenerate needs --project.")
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


def _spec_from_args(args: argparse.Namespace) -> SundialSpec:
    """Build a SundialSpec from CLI args."""
    lat, lon = resolve_location(args)
    if abs(lat) > MAX_LATITUDE:
        raise SystemExit(f"error: latitude {lat:g}° is outside the supported range ±{MAX_LATITUDE:g}°.")
    tz_str = args.timezone or timezone_at(lat=lat, lng=lon) or "UTC"
    tz = ZoneInfo(tz_str)
    year = args.year if args.year is not None else datetime.now(tz=tz).year
    try:
        return SundialSpec(
            location=Location(lat=lat, lon=lon, timezone=tz_str, name=args.location),
            timeframe=solstice_timeframe(year, args.period, tz),
            plumb_length=args.plumb_length,
            grid=GridConfig(
                dayline_day_step_days=args.dayline_day_step,
                line_points=args.line_points,
                hourline_day_step_days=args.hourline_day_step,
                time_step_minutes=args.time_step,
            ),
            year=year,
            period=args.period,
        )
    except ValueError as exc:
        raise SystemExit(f"error: {exc}")


def _default_project_dir(spec: SundialSpec) -> Path:
    """``<location-slug>_<year>_p<period>``, e.g. ``planaltina-df_2026_p0``."""
    loc = spec.location
    if loc.name:
        base = re.sub(r"[^a-z0-9]+", "-", loc.name.lower()).strip("-")
    else:
        base = f"lat{loc.lat:.2f}_lon{loc.lon:.2f}"
    return Path(f"{base}_{spec.year}_p{spec.period}")


def _provenance() -> dict[str, str]:
    def _version(pkg: str) -> str:
        try:
            return version(pkg)
        except PackageNotFoundError:
            return "unknown"

    return {
        "accuratum": _version("accuratum"),
        "astropy": _version("astropy"),
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


# --- render hints ------------------------------------------------------------


def _render_hints(args: argparse.Namespace, saved: RenderHints | None) -> RenderHints:
    """Merge render flags over *saved* hints (or the defaults). Flags win."""
    base = saved or default_render_hints()
    overlays = list(base.overlays)
    for name, path, rect in (("logo", args.logo, args.logo_rect), ("compass", args.compass, args.compass_rect)):
        if path is None and rect is None:
            continue
        index = next((i for i, o in enumerate(overlays) if o.name == name), None)
        current = overlays[index] if index is not None else DEFAULT_OVERLAYS[name]
        updated = replace(
            current,
            image_path=_portable_path(path) if path is not None else current.image_path,
            rect=rect if rect is not None else current.rect,
        )
        if index is None:
            overlays.append(updated)
        else:
            overlays[index] = updated
    return replace(
        base,
        overlays=overlays,
        label_fontsize=args.label_fontsize if args.label_fontsize is not None else base.label_fontsize,
        dayline_color=args.dayline_color or base.dayline_color,
        hourline_color=args.hourline_color or base.hourline_color,
    )


def _portable_path(path: str) -> str:
    """User-given image paths are stored absolute, so the project works from any directory."""
    return os.path.abspath(path)


def _resolved(hints: RenderHints) -> RenderHints:
    """Resolve ``accuratum:`` image paths and check that every overlay file exists."""
    overlays = []
    for overlay in hints.overlays:
        try:
            path = resolve_image_path(overlay.image_path)
        except ValueError as exc:
            raise SystemExit(f"error: {overlay.name or 'overlay'} {exc}")
        if not os.path.isfile(path):
            raise SystemExit(f"error: {overlay.name or 'overlay'} file not found: {path}")
        overlays.append(replace(overlay, image_path=path))
    return replace(hints, overlays=overlays)


def _titled(plot: Plot, args: argparse.Namespace) -> Plot:
    """Replace the plot's title and subtitle with the ones given by flag."""
    return replace(
        plot,
        title=args.title if args.title is not None else plot.title,
        subtitle=args.subtitle if args.subtitle is not None else plot.subtitle,
    )


def _kept(saved: str | None, old_default: str, new_default: str) -> str:
    """A text edited by hand survives a regenerate; a default one follows the new spec."""
    return new_default if saved is None or saved == old_default else saved


# --- modes -------------------------------------------------------------------


def _generate(args: argparse.Namespace) -> tuple[Project, Path]:
    spec = _spec_from_args(args)
    folder = Path(args.project_dir) if args.project_dir else _default_project_dir(spec)
    if (folder / PROJECT_FILE).exists() and not args.force:
        raise SystemExit(
            f"error: {folder} already holds a project; use --project {folder} to render it, or --force to overwrite."
        )
    render = _render_hints(args, None)
    _resolved(render)  # fail on a missing image before the slow computation
    project = Project(spec=spec, plot=_titled(build_plot(spec), args), render=render, provenance=_provenance())
    save_project(project, folder)
    print(f"Saved project to {folder}/")
    return project, folder


def _regenerate(folder: Path) -> Project:
    """Recompute *folder*'s project from its spec; the timeframe follows year/period."""
    data = json.loads((folder / PROJECT_FILE).read_text(encoding="utf-8"))
    spec = spec_from_dict(data["spec"])
    old_title, old_subtitle = default_title(spec), default_subtitle(spec)
    if spec.year is not None and spec.period is not None:
        spec.timeframe = solstice_timeframe(spec.year, spec.period, ZoneInfo(spec.location.timezone))
    render = hints_from_dict(data.get("render", {}))
    shutil.copyfile(folder / PROJECT_FILE, folder / (PROJECT_FILE + ".bak"))
    plot = build_plot(spec)
    plot = replace(
        plot,
        title=_kept(data.get("title"), old_title, plot.title),
        subtitle=_kept(data.get("subtitle"), old_subtitle, plot.subtitle),
    )
    project = Project(spec=spec, plot=plot, render=render, provenance=_provenance())
    save_project(project, folder)
    print(f"Regenerated {folder}/ (previous file kept as {PROJECT_FILE}.bak)")
    return project


def _open(args: argparse.Namespace) -> tuple[Project, Path]:
    folder = Path(args.project)
    if not (folder / PROJECT_FILE).is_file():
        raise SystemExit(f"error: no {PROJECT_FILE} in {folder}")
    try:
        if args.regenerate:
            return _regenerate(folder), folder
        return load_project(folder), folder
    except StaleProjectError as exc:
        raise SystemExit(f"error: {exc} Run with --project {folder} --regenerate.")
    except ValueError as exc:
        raise SystemExit(f"error: {folder / PROJECT_FILE}: {exc}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    project, folder = _open(args) if args.project is not None else _generate(args)
    hints = _resolved(_render_hints(args, project.render))
    output = args.output or str(folder / DEFAULT_OUTPUT_NAME)
    _save(_titled(project.plot, args), hints, output)
    print(f"Saved Accuratum clock to {output}")
    return 0


def _save(plot: Plot, hints: RenderHints, output: str) -> None:
    """Render with matplotlib; the extension (.png, .pdf, .svg, ...) picks the format."""
    fig, _ = matplotlib_backend.render(plot, hints)
    fig.savefig(output, dpi=200, bbox_inches="tight")


__all__ = ["build_parser", "main", "parse_lat_long", "parse_rect", "resolve_location"]


if __name__ == "__main__":
    sys.exit(main())
